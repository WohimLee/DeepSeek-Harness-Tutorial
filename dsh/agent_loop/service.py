"""Default serial M2 driver for one-step, tool-free Agent turns."""

from __future__ import annotations

import asyncio
from typing import cast

from dsh.agent import Agent, AgentId, AgentOptions, AgentRegistry, AgentStatus
from dsh.cordis import Context, Service
from dsh.llm import BlockAssembler, GenerateRequest, LlmError, LlmFailure, LlmRuntime, Message
from dsh.session import (
    AssistantChunkData,
    AssistantMessageData,
    SessionId,
    SessionStore,
    StepEndData,
    StepStartData,
    TurnEndData,
    TurnStartData,
)
from dsh.system_prompt import AssembleContext, SystemPrompt


class AgentLoop(Service):
    """Create Agents and drive queued user input through one model request."""

    name = "agent-loop"
    provide = "agentLoop"
    inject = ("agents", "llm", "sessions", "systemPrompt")

    def __init__(self, context: Context, config: object = None) -> None:
        super().__init__(context)
        self._agents = cast(AgentRegistry, context.get("agents"))
        self._llm = cast(LlmRuntime, context.get("llm"))
        self._sessions = cast(SessionStore, context.get("sessions"))
        self._prompt = cast(SystemPrompt, context.get("systemPrompt"))
        self._tasks: dict[AgentId, asyncio.Task[None]] = {}
        self._turns: dict[AgentId, int] = {}
        context.effect(lambda: self._cleanup, "agent-loop tasks")

    def create(
        self,
        session_id: SessionId,
        options: AgentOptions,
        *,
        agent_id: AgentId | None = None,
    ) -> Agent:
        """Create and publish one idle Agent after validating all identifiers."""

        resolved_id = agent_id or AgentId(str(session_id))
        if not resolved_id:
            raise ValueError("agent id must be non-empty")
        if any(agent.id == resolved_id for agent in self._agents.list_agents()):
            raise ValueError(f"agent {resolved_id!r} already exists")
        session = self._sessions.create(session_id)
        agent = Agent(resolved_id, session, options, self._wake, self._cancel)
        self._agents.register(agent)
        self._turns[resolved_id] = 0
        return agent

    def _wake(self, agent: Agent) -> None:
        task = self._tasks.get(agent.id)
        if task is None or task.done():
            agent._idle.clear()
            self._tasks[agent.id] = asyncio.create_task(
                self._drive(agent),
                name=f"agent-loop:{agent.id}",
            )

    def _cancel(self, agent: Agent) -> None:
        task = self._tasks.get(agent.id)
        if task is not None and not task.done():
            task.cancel()

    async def _drive(self, agent: Agent) -> None:
        self._set_status(agent, AgentStatus.RUNNING)
        try:
            while agent.inbox:
                messages = agent._claim()
                if messages:
                    await self._run_turn(agent, messages)
        finally:
            self._set_status(agent, AgentStatus.IDLE)
            agent._idle.set()

    async def _run_turn(self, agent: Agent, messages: tuple[Message, ...]) -> None:
        turn = self._turns[agent.id] + 1
        self._turns[agent.id] = turn
        step = 1
        session = agent.session
        session.append("turn/start", TurnStartData(turn))
        session.append("step/start", StepStartData(turn, step))
        for message in messages:
            session.append("user/message", message)

        assembler = BlockAssembler()
        try:
            assembly = await self._prompt.assemble(AssembleContext(str(agent.id)))
            request = GenerateRequest(
                agent.options.provider,
                agent.options.model,
                session.derive_messages(),
                system=assembly.text or None,
                max_tokens=agent.options.max_tokens,
            )
            async for chunk in self._llm.stream(request):
                session.append("assistant/chunk", AssistantChunkData(turn, step, chunk))
                assembler.push(chunk)
        except asyncio.CancelledError:
            failure = LlmFailure("agent turn was cancelled", "ABORTED")
            self._close_failed(agent, turn, step, failure, aborted=True)
            return
        except BaseException as error:
            failure = (
                error.failure()
                if isinstance(error, LlmError)
                else LlmFailure(str(error) or type(error).__name__, "UNKNOWN")
            )
            self._close_failed(agent, turn, step, failure, aborted=False)
            return

        finish = assembler.finish
        if finish.kind in {"error", "aborted"}:
            assert finish.failure is not None
            self._close_failed(
                agent,
                turn,
                step,
                finish.failure,
                aborted=finish.kind == "aborted",
            )
            return

        assistant = assembler.message(provider=request.provider, model=request.model)
        session.append(
            "assistant/message",
            AssistantMessageData(turn, step, assistant, assembler.usage),
        )
        session.append("step/end", StepEndData(turn, step))
        if finish.kind == "max-tokens":
            session.append("turn/end", TurnEndData(turn, "max-tokens"))
        else:
            session.append("turn/end", TurnEndData(turn, "completed"))
        agent.last_error = None

    def _close_failed(
        self,
        agent: Agent,
        turn: int,
        step: int,
        failure: LlmFailure,
        *,
        aborted: bool,
    ) -> None:
        agent.last_error = failure
        agent.session.append("step/end", StepEndData(turn, step))
        reason = "aborted" if aborted else "error"
        if reason == "aborted":
            agent.session.append("turn/end", TurnEndData(turn, "aborted"))
        else:
            agent.session.append("turn/end", TurnEndData(turn, "error"))
        self.context.emit("agent/request-error", agent, failure)

    def _set_status(self, agent: Agent, status: AgentStatus) -> None:
        if agent.status is status:
            return
        agent.status = status
        self.context.emit("agent/status", agent, status)

    async def _cleanup(self) -> None:
        tasks = tuple(task for task in self._tasks.values() if not task.done())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()


plugin = AgentLoop
