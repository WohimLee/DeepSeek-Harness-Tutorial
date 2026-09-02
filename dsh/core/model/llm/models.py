"""Immutable provider-neutral messages, content blocks, and stream chunks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, NewType
from uuid import uuid4

from .errors import LlmFailure

MessageId = NewType("MessageId", str)
CallId = NewType("CallId", str)


@dataclass(frozen=True, slots=True)
class TextBlock:
    """Plain text visible to the user and model."""

    text: str
    type: Literal["text"] = "text"


@dataclass(frozen=True, slots=True)
class ReasoningBlock:
    """Model reasoning kept distinct from visible text."""

    text: str
    type: Literal["reasoning"] = "reasoning"


@dataclass(frozen=True, slots=True)
class ToolCallBlock:
    """One provider-issued tool invocation."""

    id: CallId
    name: str
    arguments: str
    type: Literal["tool-call"] = "tool-call"


@dataclass(frozen=True, slots=True)
class ToolResultBlock:
    """Model-facing result correlated with a tool call."""

    tool_call_id: CallId
    content: tuple[ContentBlock, ...]
    is_error: bool = False
    type: Literal["tool-result"] = "tool-result"


type ContentBlock = TextBlock | ReasoningBlock | ToolCallBlock | ToolResultBlock


@dataclass(frozen=True, slots=True)
class UserSource:
    """Direct human input."""

    kind: Literal["user"] = "user"


@dataclass(frozen=True, slots=True)
class PluginSource:
    """Synthetic context contributed by a named plugin."""

    plugin: str
    kind: Literal["plugin"] = "plugin"


@dataclass(frozen=True, slots=True)
class ModelSource:
    """Provider/model identity that produced an assistant message."""

    provider: str
    model: str
    kind: Literal["model"] = "model"


@dataclass(frozen=True, slots=True)
class ToolSource:
    """Tool call identity that produced a user-role result."""

    call_id: CallId
    kind: Literal["tool"] = "tool"


type MessageSource = UserSource | PluginSource | ModelSource | ToolSource
type MessageRole = Literal["system", "user", "assistant"]


@dataclass(frozen=True, slots=True)
class Message:
    """Identified immutable value shared by delivery, log, and LLM request."""

    id: MessageId
    role: MessageRole
    content: tuple[ContentBlock, ...]
    source: MessageSource


type AssistantMessage = Message


def _message_id() -> MessageId:
    return MessageId(str(uuid4()))


def create_user_message(
    content: tuple[ContentBlock, ...],
    source: UserSource | PluginSource | ToolSource | None = None,
) -> Message:
    """Create an identified user-role message."""

    return Message(_message_id(), "user", tuple(content), source or UserSource())


def create_assistant_message(
    content: tuple[ContentBlock, ...],
    *,
    provider: str,
    model: str,
) -> Message:
    """Create an identified model-produced assistant message."""

    return Message(_message_id(), "assistant", tuple(content), ModelSource(provider, model))


def create_tool_result_message(
    call_id: CallId,
    content: tuple[ContentBlock, ...],
    *,
    is_error: bool = False,
) -> Message:
    """Create one user-role message containing a correlated tool result."""

    block = ToolResultBlock(call_id, tuple(content), is_error)
    return create_user_message((block,), ToolSource(call_id))


@dataclass(frozen=True, slots=True)
class TokenUsage:
    """Disjoint token accounting for one provider request."""

    input_tokens: int
    output_tokens: int
    cache_read_tokens: int | None = None
    cache_write_tokens: int | None = None
    reasoning_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class FinishReason:
    """Why a model response stopped."""

    kind: Literal["stop", "tool-calls", "max-tokens", "aborted", "error"]
    failure: LlmFailure | None = None

    def __post_init__(self) -> None:
        failed = self.kind in {"aborted", "error"}
        if failed != (self.failure is not None):
            raise ValueError("failure is required exactly for aborted/error finish reasons")


@dataclass(frozen=True, slots=True)
class BlockStart:
    index: int
    block_type: str
    type: Literal["block-start"] = "block-start"


@dataclass(frozen=True, slots=True)
class TextDelta:
    index: int
    text: str
    type: Literal["text-delta"] = "text-delta"


@dataclass(frozen=True, slots=True)
class ReasoningDelta:
    index: int
    text: str
    type: Literal["reasoning-delta"] = "reasoning-delta"


@dataclass(frozen=True, slots=True)
class ToolCallDelta:
    index: int
    arguments_delta: str
    id: CallId | None = None
    name: str | None = None
    type: Literal["tool-call-delta"] = "tool-call-delta"


@dataclass(frozen=True, slots=True)
class BlockEnd:
    index: int
    block: ContentBlock
    type: Literal["block-end"] = "block-end"


@dataclass(frozen=True, slots=True)
class UsageChunk:
    usage: TokenUsage
    type: Literal["usage"] = "usage"


@dataclass(frozen=True, slots=True)
class FinishChunk:
    reason: FinishReason
    type: Literal["finish"] = "finish"


type AssistantChunk = (
    BlockStart | TextDelta | ReasoningDelta | ToolCallDelta | BlockEnd | UsageChunk | FinishChunk
)
type StreamChunk = AssistantChunk


@dataclass(frozen=True, slots=True)
class ToolSchema:
    """Provider-neutral tool declaration."""

    name: str
    description: str
    parameters: dict[str, object]


@dataclass(frozen=True, slots=True)
class GenerateRequest:
    """One fully assembled provider-neutral model request."""

    provider: str
    model: str
    messages: tuple[Message, ...]
    system: str | None = None
    tools: tuple[ToolSchema, ...] = ()
    temperature: float | None = None
    max_tokens: int | None = None
    stop: tuple[str, ...] = ()
