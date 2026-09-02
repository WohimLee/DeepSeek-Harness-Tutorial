"""Adapter registry and stream normalization contracts."""

from collections.abc import AsyncIterator
from typing import cast

import pytest

from dsh.cordis import Context
from dsh.core.model.llm import (
    FinishChunk,
    FinishReason,
    GenerateRequest,
    LlmAdapter,
    LlmError,
    LlmRuntime,
    StreamChunk,
    TextDelta,
    plugin,
)


class Adapter:
    def __init__(self, *, fail: bool = False, finish: bool = True) -> None:
        self.fail = fail
        self.finish = finish

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        yield TextDelta(0, "hello")
        if self.fail:
            raise RuntimeError("provider failed")
        if self.finish:
            yield FinishChunk(FinishReason("stop"))


async def _collect(runtime: LlmRuntime, request: GenerateRequest) -> list[StreamChunk]:
    return [chunk async for chunk in runtime.stream(request)]


async def test_registration_is_owned_by_provider_fiber() -> None:
    context = Context()
    runtime_fiber = context.plugin(plugin)
    await runtime_fiber.wait()
    runtime = cast(LlmRuntime, context.get("llm"))

    class ProviderPlugin:
        inject = ("llm",)

        def apply(self, ctx: Context, config: object) -> None:
            llm = cast(LlmRuntime, ctx.get("llm"))
            llm.register_adapter(("test",), cast(LlmAdapter, Adapter()))

    provider = context.plugin(ProviderPlugin())
    await provider.wait()
    assert runtime.providers() == ("test",)

    await provider.dispose()
    assert runtime.providers() == ()
    await context.aclose()


async def test_stream_adds_missing_finish_and_normalizes_provider_failure() -> None:
    context = Context()
    runtime_fiber = context.plugin(plugin)
    await runtime_fiber.wait()
    runtime = cast(LlmRuntime, context.get("llm"))
    request = GenerateRequest("test", "model", ())

    runtime.register_adapter(("test",), cast(LlmAdapter, Adapter(finish=False)))
    chunks = await _collect(runtime, request)
    assert isinstance(chunks[-1], FinishChunk)
    assert chunks[-1].reason.kind == "stop"

    await context.aclose()

    context = Context()
    runtime_fiber = context.plugin(plugin)
    await runtime_fiber.wait()
    runtime = cast(LlmRuntime, context.get("llm"))
    runtime.register_adapter(("test",), cast(LlmAdapter, Adapter(fail=True)))
    chunks = await _collect(runtime, request)
    assert isinstance(chunks[-1], FinishChunk)
    assert chunks[-1].reason.kind == "error"
    assert chunks[-1].reason.failure is not None
    assert chunks[-1].reason.failure.message == "provider failed"
    await context.aclose()


async def test_unknown_provider_fails_before_streaming() -> None:
    context = Context()
    runtime_fiber = context.plugin(plugin)
    await runtime_fiber.wait()
    runtime = cast(LlmRuntime, context.get("llm"))

    with pytest.raises(LlmError, match="no adapter"):
        await _collect(runtime, GenerateRequest("missing", "model", ()))

    await context.aclose()


async def test_duplicate_registration_is_atomic() -> None:
    context = Context()
    runtime_fiber = context.plugin(plugin)
    await runtime_fiber.wait()
    runtime = cast(LlmRuntime, context.get("llm"))
    first = cast(LlmAdapter, Adapter())
    runtime.register_adapter(("first", "shared"), first)

    with pytest.raises(LlmError) as error:
        runtime.register_adapter(("new", "shared"), cast(LlmAdapter, Adapter()))

    assert error.value.code == "DUPLICATE_ADAPTER"
    assert runtime.providers() == ("first", "shared")
    await context.aclose()
