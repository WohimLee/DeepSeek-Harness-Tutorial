"""Lifecycle-owned LLM adapter registry and streaming dispatch."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from typing import Protocol, cast

from dsh.cordis import Context, Effect, Service

from .errors import LlmError, failure_from_exception
from .models import FinishChunk, FinishReason, GenerateRequest, StreamChunk


class LlmAdapter(Protocol):
    """Provider implementation behind the LLM runtime seam."""

    def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Return one raw stream ending in a finish chunk."""


class LlmRuntime(Service):
    """Route provider-neutral requests to lifecycle-owned adapters."""

    name = "llm"
    provide = "llm"

    def __init__(self, context: Context, config: object = None) -> None:
        super().__init__(context)
        self._adapters: dict[str, LlmAdapter] = {}

    def register_adapter(self, providers: Iterable[str], adapter: LlmAdapter) -> Effect:
        """Atomically register one adapter for non-empty provider routes."""

        routes = tuple(providers)
        if not routes or any(not route for route in routes) or len(set(routes)) != len(routes):
            raise LlmError("adapter routes must be unique non-empty strings", "INVALID_ADAPTER")
        duplicate = next((route for route in routes if route in self._adapters), None)
        if duplicate is not None:
            raise LlmError(f"provider {duplicate!r} already has an adapter", "DUPLICATE_ADAPTER")
        owner = self.caller_context

        def setup() -> object:
            self._adapters.update((route, adapter) for route in routes)
            self.context.emit("llm/adapters-updated")

            def cleanup() -> None:
                for route in routes:
                    if self._adapters.get(route) is adapter:
                        del self._adapters[route]
                self.context.emit("llm/adapters-updated")

            return cleanup

        return owner.effect(setup, f"llm.register_adapter({routes!r})")

    def providers(self) -> tuple[str, ...]:
        """List active provider routes in registration order."""

        return tuple(self._adapters)

    def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        """Capture caller context and dispatch one normalized stream."""

        caller = self.caller_context
        return self._stream(caller, request)

    async def _stream(
        self,
        context: Context,
        request: GenerateRequest,
    ) -> AsyncIterator[StreamChunk]:
        adapter = self._adapters.get(request.provider)
        if adapter is None:
            raise LlmError(f"no adapter for provider {request.provider!r}", "NO_ADAPTER")
        candidate = await context.waterfall(
            "llm/stream",
            request,
            next_=lambda: adapter.stream(request),
        )
        stream = cast(AsyncIterator[StreamChunk], candidate)
        finished = False
        try:
            async for chunk in stream:
                yield chunk
                if isinstance(chunk, FinishChunk):
                    finished = True
                    return
        except asyncio.CancelledError as error:
            yield FinishChunk(
                FinishReason("aborted", failure_from_exception(error)),
            )
            return
        except BaseException as error:
            yield FinishChunk(FinishReason("error", failure_from_exception(error)))
            return
        if not finished:
            yield FinishChunk(FinishReason("stop"))


plugin = LlmRuntime
