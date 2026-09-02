"""Scripted Provider configuration and deterministic output."""

from typing import cast

from dsh.cordis import Context
from dsh.core.model.llm import FinishChunk, FinishReason, GenerateRequest, LlmRuntime, TextDelta
from dsh.plugins.providers.model.llm_scripted import plugin


async def test_scripted_plugin_consumes_responses_in_order() -> None:
    context = Context()
    llm_fiber = context.plugin(LlmRuntime)
    await llm_fiber.wait()
    provider = context.plugin(plugin, {"responses": ["first", "second"]})
    await provider.wait()
    runtime = cast(LlmRuntime, context.get("llm"))

    first = [chunk async for chunk in runtime.stream(GenerateRequest("scripted", "model", ()))]
    second = [chunk async for chunk in runtime.stream(GenerateRequest("scripted", "model", ()))]

    assert first == [TextDelta(0, "first"), FinishChunk(FinishReason("stop"))]
    assert second[0] == TextDelta(0, "second")
    assert isinstance(second[-1], FinishChunk)

    await provider.dispose()
    assert runtime.providers() == ()
    await context.aclose()
