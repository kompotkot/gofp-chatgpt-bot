# gofp-chatgpt-bot

ChatGPT bot for The Garden of Forking Paths game.

## Deployment

Generate interface from ABI:

```bash
moonworm generate-brownie --name gofp -o gcb -p gcb
```

Add Constellation Wyrm network to brownie:

```bash
brownie networks add Constellation wyrm host=https://wyrm.0xconstellation.com/http chainid=322
```

Get all models of ChatGPT:

```bash
curl https://api.openai.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY" | jq .data[].id
```

Get number of sessions:

```bash
python -m gcb.gofp num-sessions --network wyrm --address "$GOFP_CONTRACT_ADDRESS"
```

GOFP docs with methods available at https://docs.moonstream.to/engine/mechanics/garden-of-forking-paths.

Play:

```bash
gcb play --address "$GOFP_CONTRACT_ADDRESS" --network wyrm --confirmations 0 --sender "$DEV_KEYFILE" --password "$DEV_KEYFILE_PASSOWRD" --session 4 --token 2
```
