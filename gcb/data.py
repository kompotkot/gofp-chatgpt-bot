from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


class Method(Enum):
    GET = "get"
    POST = "post"


class SessionInfo(BaseModel):
    player_token_address: str
    payment_token_address: str
    payment_amount: int
    is_active: bool
    is_choosing_active: bool
    uri: str
    stages: List[int] = Field(default_factory=list)
    is_forgiving: bool


class SessionDataStagePaths(BaseModel):
    path: int
    title: str
    lore: str
    image_url: str


class SessionDataStages(BaseModel):
    stage: int
    title: str
    lore: str
    image_url: str
    paths: List[SessionDataStagePaths] = Field(default_factory=list)


class SessionData(BaseModel):
    title: str
    lore: str
    image_url: str
    stages: List[SessionDataStages] = Field(default_factory=list)
