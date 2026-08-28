"""Raw stream assembly contracts."""

from dsh.llm import (
    BlockAssembler,
    CallId,
    FinishChunk,
    FinishReason,
    ReasoningBlock,
    ReasoningDelta,
    TextBlock,
    TextDelta,
    ToolCallBlock,
    ToolCallDelta,
)


def test_assembler_preserves_block_order_and_deltas() -> None:
    assembler = BlockAssembler()
    assembler.push(ReasoningDelta(0, "think "))
    assembler.push(ReasoningDelta(0, "first"))
    assembler.push(TextDelta(1, "answer"))
    assembler.push(FinishChunk(FinishReason("stop")))

    assert assembler.blocks() == (
        ReasoningBlock("think first"),
        TextBlock("answer"),
    )


def test_max_tokens_drops_incomplete_tool_call() -> None:
    assembler = BlockAssembler()
    assembler.push(ToolCallDelta(0, '{"value":', CallId("call-1"), "echo"))
    assembler.push(FinishChunk(FinishReason("max-tokens")))

    assert assembler.blocks() == ()


def test_tool_call_assembles_raw_arguments() -> None:
    assembler = BlockAssembler()
    assembler.push(ToolCallDelta(0, '{"value":', CallId("call-1"), "echo"))
    assembler.push(ToolCallDelta(0, '"ok"}'))
    assembler.push(FinishChunk(FinishReason("tool-calls")))

    assert assembler.blocks() == (
        ToolCallBlock(CallId("call-1"), "echo", '{"value":"ok"}'),
    )
