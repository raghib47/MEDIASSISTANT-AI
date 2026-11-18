"""Pydantic models for the /chat endpoint."""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.config import get_settings

_settings = get_settings()

# Assistant replies are longer than user messages, so history items get a larger cap.
HISTORY_ITEM_MAX_CHARS = 6000
MAX_HISTORY_ITEMS_ACCEPTED = 40  # hard cap on what we even parse; the service trims further

# Whitespace is stripped BEFORE length checks, so "   " is rejected as empty.
UserText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=_settings.max_message_chars),
]
HistoryText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=HISTORY_ITEM_MAX_CHARS),
]


class HistoryMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: HistoryText


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: UserText
    history: list[HistoryMessage] = Field(default_factory=list, max_length=MAX_HISTORY_ITEMS_ACCEPTED)


class ChatResponse(BaseModel):
    reply: str
    language: Literal["en", "bn"]
    emergency: bool = False
    # "safety_engine" = deterministic rules answered (LLM was NOT called); "llm" = model answered
    source: Literal["safety_engine", "llm"]
    # Rule IDs that fired (e.g. ["chest_pain"]); empty for normal answers
    emergency_signs: list[str] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
