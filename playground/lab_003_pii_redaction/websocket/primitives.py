from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, RootModel


class WSMessageTypes(StrEnum):
    TOGGLE = "toggle"
    CHAT = "chat"


class WSToggleMessage(BaseModel):
    type: Literal[WSMessageTypes.TOGGLE]
    protected: bool


class WSChatMessage(BaseModel):
    type: Literal[WSMessageTypes.CHAT]
    message: str


WSMessage = RootModel[WSToggleMessage | WSChatMessage | str]
