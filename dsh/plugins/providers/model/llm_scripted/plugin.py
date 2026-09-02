"""Scripted adapter and its Cordis Provider plugin."""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, cast

from dsh.cordis import Context
from dsh.core.model.llm import (
    FinishChunk,
    FinishReason,
    GenerateRequest,
    LlmAdapter,
    StreamChunk,
    TextDelta,
)

from .config import Config as ScriptedConfig


@dataclass(slots=True)
class ScriptedAdapter:
    """Return one deterministic text response per request and capture requests."""

    responses: list[str]
    requests: list[GenerateRequest] = field(default_factory=list)

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        if not self.responses:
            raise RuntimeError("scripted response queue is empty")
        yield TextDelta(0, self.responses.pop(0))
        yield FinishChunk(FinishReason("stop"))


class _LlmRegistry(Protocol):
    def register_adapter(self, providers: tuple[str, ...], adapter: LlmAdapter) -> object: ...


@dataclass(frozen=True, slots=True)
class ScriptedPlugin:
    """Register a configured deterministic adapter."""

    name = "llm-scripted"
    inject = ("llm",)
    Config = ScriptedConfig

    def apply(self, ctx: Context, config: ScriptedConfig) -> None:
        llm = cast(_LlmRegistry, ctx.get("llm"))
        llm.register_adapter((config.provider,), ScriptedAdapter(list(config.responses)))


plugin = ScriptedPlugin()
