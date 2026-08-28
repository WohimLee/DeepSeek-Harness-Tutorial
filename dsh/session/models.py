"""Immutable event envelope and core Harness event payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType

from dsh.llm import CallId, Message, StreamChunk, TokenUsage

SessionId = NewType("SessionId", str)

type EventType = Literal[
    "turn/start",
    "turn/end",
    "step/start",
    "step/end",
    "user/message",
    "assistant/chunk",
    "assistant/message",
    "tool/call",
    "tool/result",
]


@dataclass(frozen=True, slots=True)
class TurnStartData:
    turn: int


@dataclass(frozen=True, slots=True)
class TurnEndData:
    turn: int
    reason: Literal["completed", "aborted", "blocked", "error", "max-tokens"]


@dataclass(frozen=True, slots=True)
class StepStartData:
    turn: int
    step: int


@dataclass(frozen=True, slots=True)
class StepEndData:
    turn: int
    step: int


@dataclass(frozen=True, slots=True)
class AssistantChunkData:
    turn: int
    step: int
    chunk: StreamChunk


@dataclass(frozen=True, slots=True)
class AssistantMessageData:
    turn: int
    step: int
    message: Message
    usage: TokenUsage | None = None
    interrupted: bool = False


@dataclass(frozen=True, slots=True)
class ToolCallData:
    turn: int
    step: int
    call_id: CallId
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class ToolResultData:
    turn: int
    step: int
    message: Message
    error_name: str | None = None
    error_code: str | None = None


type EventData = (
    TurnStartData
    | TurnEndData
    | StepStartData
    | StepEndData
    | Message
    | AssistantChunkData
    | AssistantMessageData
    | ToolCallData
    | ToolResultData
)


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """One contiguous append-only event envelope."""

    type: EventType
    seq: int
    time_ms: int
    data: EventData
