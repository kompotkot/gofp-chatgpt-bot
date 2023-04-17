import argparse
import json
import logging
import os
from typing import Any

import requests
from brownie import network

from . import data
from .gofp import add_default_arguments, get_transaction_config, gofp  # type: ignore

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OPENAPI_BASE_URL = "https://api.openai.com/v1/chat"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY is None:
    raise ValueError("OPENAI_API_KEY environment variable must be set")


def requests_call(
    method: data.Method,
    url: str,
    timeout: float = 15,
    **kwargs,
) -> Any:
    try:
        response = requests.request(method.value, url=url, timeout=timeout, **kwargs)
        response.raise_for_status()
    except Exception as e:
        raise Exception(str(e))
    return response.json()


def handle_play(args: argparse.Namespace) -> None:
    """
    Handle The Garden of Forking Paths play automation with ChatGPT.
    """
    network.connect(args.network)
    contract = gofp(contract_address=args.address)

    # Fetch current session info from smartcontract
    session_info_raw = contract.get_session(args.session)
    session_info = data.SessionInfo(
        player_token_address=session_info_raw[0],
        payment_token_address=session_info_raw[1],
        payment_amount=session_info_raw[2],
        is_active=session_info_raw[3],
        is_choosing_active=session_info_raw[4],
        uri=session_info_raw[5],
        stages=session_info_raw[6],
        is_forgiving=session_info_raw[7],
    )

    if not session_info.is_active:
        logger.error(f"Session {args.session} is not active")
        return
    if not session_info.is_choosing_active:
        logger.error(f"Session {args.session} is not ready to accept choosing")
        return

    logger.info(
        f"Fetch session {args.session} with stages {session_info.stages} and uri {session_info.uri}"
    )

    # Fetch active stage
    # Stage number returned 1-indexed for frontend UI
    current_stage_indexed = contract.get_current_stage(args.session)
    current_stage = current_stage_indexed - 1
    logger.info(f"Current stage of session {args.session} is {current_stage}")

    # Fetch title, lore, paths from stage URI
    try:
        session_data_raw = requests_call(method=data.Method.GET, url=session_info.uri)
    except Exception as err:
        logger.error(f"Unable to get response from URI, err: {err}")
        return

    session_data = data.SessionData(
        title=session_data_raw["title"],
        lore=session_data_raw["lore"],
        image_url=session_data_raw["imageUrl"],
        stages=[
            data.SessionDataStages(
                stage=i,
                title=stage["title"],
                lore=stage["lore"],
                image_url=stage["imageUrl"],
                paths=[
                    data.SessionDataStagePaths(
                        path=j,
                        title=path["title"],
                        lore=path["lore"],
                        image_url=path["imageUrl"],
                    )
                    for j, path in enumerate(stage["paths"])
                ],
            )
            for i, stage in enumerate(session_data_raw["stages"])
        ],
    )
    logger.info(
        f"Fetch session data with title {session_data.title} and active stage title {session_data.stages[current_stage].title}"
    )

    # Generate a question for ChatGPT
    # It should understand the rules and response to us in JSON format
    paths = ""
    for i, path in enumerate(session_data.stages[current_stage].paths):
        paths += f"- Path {i} - {path.title} - {path.lore}\n\n"

    message_to_bot = f"""Let's play. I will provide you with a short lore containing different paths to choose from. Please respond in JSON format. You should select one correct path and place it under the key 'answer' and provide an explanation for your choice under the key 'description'.
    
The lore: {session_data.stages[current_stage].lore}
Paths:
{paths}
"""
    openapi_headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
    }
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": message_to_bot}],
    }
    logger.info("Asking ChatGPT to choose path")
    if not args.mock:
        try:
            bot_resp_raw = requests_call(
                method=data.Method.POST,
                url=f"{OPENAPI_BASE_URL}/completions",
                headers=openapi_headers,
                json=payload,
                timeout=60,
            )
        except Exception as err:
            logger.error(f"Unable to get response from ChatGPT, err: {err}")
            return
    else:
        bot_resp_raw = {
            "id": "chatcmpl-422",
            "object": "chat.completion",
            "created": 1681311158,
            "model": "gpt-3.5-turbo-0301",
            "usage": {"prompt_tokens": 825, "completion_tokens": 78, "total_tokens": 903},
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": '{\n    "answer": 0,\n    "description": "I would back the Copper hound because it has a useful skill that people could benefit from by sniffing out copper deposits. Additionally, they seem to be domesticated dogs so they may be more manageable than some of the other creatures. The downside is that they are not the most pleasant smelling animals and can be quite loud."\n}',
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
        }

    # Parse ChatGPT response
    bot_choices = bot_resp_raw.get("choices", "")
    if bot_choices == "":
        logger.error(
            f"ChatGTP did not provide any choices, bot_resp_raw: {bot_resp_raw}"
        )
        return

    bot_replies = []
    for choice in bot_resp_raw["choices"]:
        bot_message = choice.get("message", "")
        if bot_message != "":
            bot_message_content = bot_message.get("content", "")
            if bot_message_content != "":
                bot_replies.append(bot_message_content)

    bot_replies_len = len(bot_replies)
    if bot_replies_len != 1:
        logger.error(f"Incorrect ChatGPT bot_replies length: {bot_replies_len}")
        return

    bot_answer = 0
    bot_answer_description = ""
    try:
        bot_reply = json.loads(bot_replies[0])
        bot_answer = int(bot_reply["answer"])
        bot_answer_description = bot_reply["description"]
    except Exception:
        logger.error(f"ChatGPT provided answer in incorrect format: {bot_replies[0]}")
        return

    logger.info(
        f"Bot answer is: {bot_answer} and description: {bot_answer_description}"
    )

    # Send transaction with a choice
    transaction_config = get_transaction_config(args)

    tx_hash = ""
    if not args.dry_run:
        tx_hash = contract.choose_current_stage_paths(
            session_id=args.session, token_ids=[args.token], paths=[bot_answer + 1], transaction_config=transaction_config
        )
    logger.info(f"Successfully sent transaction: {tx_hash}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="The Garden of Forking Paths ChatGPT bot CLI"
    )
    parser.set_defaults(func=lambda _: parser.print_help())
    subcommands = parser.add_subparsers(description="GCB commands")

    parser_play = subcommands.add_parser("play", description="Play commands")
    parser_play.set_defaults(func=lambda _: parser_play.print_help())

    # Add default arguments for brownie
    add_default_arguments(parser=parser_play, transact=True)

    parser_play.add_argument(
        "-s",
        "--session",
        required=True,
        type=int,
        help="Session to play",
    )
    parser_play.add_argument(
        "-t",
        "--token",
        required=True,
        type=int,
        help="Token ID",
    )
    parser_play.add_argument(
        "--mock",
        action="store_true",
        help="Use ChatGCP mock response",
    )
    parser_play.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not execute transaction",
    )
    parser_play.set_defaults(func=handle_play)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
