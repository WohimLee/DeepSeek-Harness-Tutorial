"""Lifecycle-owned registry of active Agent instances."""

from __future__ import annotations

from dsh.cordis import Context, Effect, Service

from .models import Agent, AgentId


class AgentRegistry(Service):
    """Publish active Agents without owning their execution policy."""

    name = "agent"
    provide = "agents"

    def __init__(self, context: Context, config: object = None) -> None:
        super().__init__(context)
        self._agents: dict[AgentId, Agent] = {}

    def register(self, agent: Agent) -> Effect:
        """Register an Agent until the calling Fiber unloads."""

        if agent.id in self._agents:
            raise ValueError(f"agent {agent.id!r} already exists")
        owner = self.caller_context

        def setup() -> object:
            self._agents[agent.id] = agent

            def cleanup() -> None:
                if self._agents.get(agent.id) is agent:
                    del self._agents[agent.id]

            return cleanup

        return owner.effect(setup, f"agents.register({agent.id!r})")

    def get_agent(self, agent_id: AgentId) -> Agent:
        """Resolve an active Agent by stable identity."""

        return self._agents[agent_id]

    def list_agents(self) -> tuple[Agent, ...]:
        """List Agents in registration order."""

        return tuple(self._agents.values())


plugin = AgentRegistry
