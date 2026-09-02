"""M2 Agent Loop completion, failure, cancellation, and lifecycle contracts."""

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import cast

import pytest

from dsh.cordis import Context, Fiber
from dsh.core.model.llm import (
    FinishChunk,
    FinishReason,
    GenerateRequest,
    LlmRuntime,
    StreamChunk,
    TextBlock,
    TextDelta,
    create_user_message,
)
from dsh.core.model.llm import plugin as llm_plugin
from dsh.core.runtime.agent import AgentId, AgentOptions, AgentRegistry
from dsh.core.runtime.agent import plugin as agent_plugin
from dsh.core.runtime.agent_loop import AgentLoop
from dsh.core.runtime.agent_loop import plugin as loop_plugin
from dsh.core.runtime.session import SessionId
from dsh.core.runtime.session import plugin as session_plugin
from dsh.core.runtime.system_prompt import plugin as prompt_plugin


@dataclass(slots=True)
class _Adapter:
    responses: list[str | BaseException]
    requests: list[GenerateRequest] = field(default_factory=list)
    wait_forever: bool = False

    async def stream(self, request: GenerateRequest) -> AsyncIterator[StreamChunk]:
        self.requests.append(request)
        if self.wait_forever:
            await asyncio.Event().wait()
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        yield TextDelta(0, response)
        yield FinishChunk(FinishReason("stop"))


async def _harness(adapter: _Adapter) -> tuple[Context, AgentLoop, Fiber]:
    context = Context()
    fibers = [
        context.plugin(llm_plugin),
        context.plugin(session_plugin),
        context.plugin(prompt_plugin, {"persona": "You are concise."}),
        context.plugin(agent_plugin),
    ]
    for fiber in fibers:
        await fiber.wait()
    llm = cast(LlmRuntime, context.get("llm"))
    llm.register_adapter(("test",), adapter)
    loop_fiber = context.plugin(loop_plugin)
    await loop_fiber.wait()
    return context, cast(AgentLoop, context.get("agentLoop")), loop_fiber


async def test_tool_free_turn_uses_log_projection_and_records_boundaries() -> None:
    adapter = _Adapter(["hello", "again"])
    context, loop, _loop_fiber = await _harness(adapter)
    agent = loop.create(SessionId("s1"), AgentOptions("test", "model"), agent_id=AgentId("a1"))

    agent.followup(create_user_message((TextBlock("first"),)))
    await agent.when_idle()
    agent.followup(create_user_message((TextBlock("second"),)))
    await agent.when_idle()

    assert adapter.requests[0].system == "You are concise."
    assert [message.content for message in adapter.requests[1].messages] == [
        (TextBlock("first"),),
        (TextBlock("hello"),),
        (TextBlock("second"),),
    ]
    assert adapter.requests[1].messages == agent.session.derive_messages()[:-1]
    assert [event.type for event in agent.session.events] == [
        "turn/start",
        "step/start",
        "user/message",
        "assistant/chunk",
        "assistant/chunk",
        "assistant/message",
        "step/end",
        "turn/end",
        "turn/start",
        "step/start",
        "user/message",
        "assistant/chunk",
        "assistant/chunk",
        "assistant/message",
        "step/end",
        "turn/end",
    ]
    await context.aclose()


async def test_provider_failure_closes_turn_without_success_message() -> None:
    context, loop, _loop_fiber = await _harness(_Adapter([RuntimeError("offline")]))
    agent = loop.create(SessionId("failure"), AgentOptions("test", "model"))

    agent.followup(create_user_message((TextBlock("hello"),)))
    await agent.when_idle()

    assert agent.last_error is not None
    assert agent.last_error.message == "offline"
    assert [event.type for event in agent.session.events][-2:] == ["step/end", "turn/end"]
    assert agent.session.events[-1].data.reason == "error"  # type: ignore[union-attr]
    assert all(event.type != "assistant/message" for event in agent.session.events)
    await context.aclose()


async def test_missing_adapter_also_closes_the_open_turn() -> None:
    context, loop, _loop_fiber = await _harness(_Adapter([]))
    agent = loop.create(SessionId("missing"), AgentOptions("missing", "model"))

    agent.followup(create_user_message((TextBlock("hello"),)))
    await agent.when_idle()

    assert agent.last_error is not None
    assert agent.last_error.code == "NO_ADAPTER"
    assert agent.session.events[-1].data.reason == "error"  # type: ignore[union-attr]
    await context.aclose()


async def test_cancel_and_plugin_unload_wait_for_driver_quiescence() -> None:
    context, loop, loop_fiber = await _harness(_Adapter([], wait_forever=True))
    registry = cast(AgentRegistry, context.get("agents"))
    agent = loop.create(SessionId("cancel"), AgentOptions("test", "model"))
    agent.followup(create_user_message((TextBlock("hang"),)))
    await asyncio.sleep(0)

    agent.cancel()
    await agent.when_idle()
    assert agent.session.events[-1].data.reason == "aborted"  # type: ignore[union-attr]

    await loop_fiber.dispose()
    with pytest.raises(KeyError):
        registry.get_agent(AgentId("cancel"))
    await context.aclose()
