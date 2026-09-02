"""Canonical incremental stream-to-message assembly."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    BlockEnd,
    BlockStart,
    CallId,
    ContentBlock,
    FinishChunk,
    FinishReason,
    Message,
    ReasoningBlock,
    ReasoningDelta,
    StreamChunk,
    TextBlock,
    TextDelta,
    TokenUsage,
    ToolCallBlock,
    ToolCallDelta,
    UsageChunk,
    create_assistant_message,
)


@dataclass(slots=True)
class _Partial:
    block_type: str
    text: str = ""
    call_id: CallId | None = None
    call_name: str | None = None
    arguments: str = ""
    closed: ContentBlock | None = None


class BlockAssembler:
    """Assemble raw provider chunks while retaining their original ordering."""

    def __init__(self) -> None:
        self._partials: dict[int, _Partial] = {}
        self._order: list[int] = []
        self.usage: TokenUsage | None = None
        self.finish = FinishReason("stop")

    def _ensure(self, index: int, block_type: str) -> _Partial:
        partial = self._partials.get(index)
        if partial is None:
            partial = _Partial(block_type)
            self._partials[index] = partial
            self._order.append(index)
        return partial

    def push(self, chunk: StreamChunk) -> None:
        """Consume one raw stream chunk."""

        match chunk:
            case BlockStart(index=index, block_type=block_type):
                self._ensure(index, block_type)
            case TextDelta(index=index, text=text):
                partial = self._ensure(index, "text")
                if partial.closed is None:
                    partial.text += text
            case ReasoningDelta(index=index, text=text):
                partial = self._ensure(index, "reasoning")
                if partial.closed is None:
                    partial.text += text
            case ToolCallDelta(
                index=index,
                arguments_delta=arguments,
                id=call_id,
                name=name,
            ):
                partial = self._ensure(index, "tool-call")
                if partial.closed is None:
                    partial.arguments += arguments
                    partial.call_id = call_id or partial.call_id
                    partial.call_name = name or partial.call_name
            case BlockEnd(index=index, block=block):
                partial = self._ensure(index, block.type)
                if partial.closed is None:
                    partial.closed = block
            case UsageChunk(usage=usage):
                self.usage = usage
            case FinishChunk(reason=reason):
                self.finish = reason

    def _assemble(self, index: int) -> ContentBlock:
        partial = self._partials[index]
        if partial.closed is not None:
            return partial.closed
        if partial.block_type == "text":
            return TextBlock(partial.text)
        if partial.block_type == "reasoning":
            return ReasoningBlock(partial.text)
        if partial.block_type == "tool-call":
            return ToolCallBlock(
                partial.call_id or CallId(f"call-{index}"),
                partial.call_name or "",
                partial.arguments,
            )
        raise ValueError(f"cannot assemble incomplete block type {partial.block_type!r}")

    def blocks(self) -> tuple[ContentBlock, ...]:
        """Return safe completed output in stream order."""

        blocks = tuple(self._assemble(index) for index in self._order)
        if self.finish.kind == "max-tokens":
            return tuple(block for block in blocks if not isinstance(block, ToolCallBlock))
        return blocks

    def message(self, *, provider: str, model: str) -> Message:
        """Create the identified assistant message for this stream."""

        return create_assistant_message(self.blocks(), provider=provider, model=model)
