"""Agent Registry unit and lifecycle contracts."""

from typing import cast

import pytest

from dsh.cordis import Context
from dsh.core.runtime.agent import Agent, AgentId, AgentOptions, AgentRegistry, plugin
from dsh.core.runtime.session import Session, SessionId


async def test_registration_is_owned_by_calling_fiber() -> None:
    context = Context()
    registry_fiber = context.plugin(plugin)
    await registry_fiber.wait()
    registry = cast(AgentRegistry, context.get("agents"))
    agent = Agent(
        AgentId("a1"),
        Session(SessionId("s1")),
        AgentOptions("scripted", "test"),
        lambda _agent: None,
        lambda _agent: None,
    )

    def owner(ctx: Context, _config: object) -> None:
        owned_registry = cast(AgentRegistry, ctx.get("agents"))
        owned_registry.register(agent)

    owner_fiber = context.plugin(owner)
    await owner_fiber.wait()
    assert registry.get_agent(AgentId("a1")) is agent

    await owner_fiber.dispose()
    with pytest.raises(KeyError):
        registry.get_agent(AgentId("a1"))
    await context.aclose()


def test_options_validate_route_and_limit() -> None:
    with pytest.raises(ValueError, match="provider and model"):
        AgentOptions("", "model")
    with pytest.raises(ValueError, match="positive"):
        AgentOptions("provider", "model", 0)
