"""Agent identity, options, and observable runtime state."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import NewType

from dsh.core.model.llm import LlmFailure, Message
from dsh.core.runtime.session import Session

AgentId = NewType("AgentId", str)


class AgentStatus(StrEnum):
    """Small M2 state machine exposed to entry adapters and tests."""

    IDLE = "idle"
    RUNNING = "running"


@dataclass(frozen=True, slots=True)
class AgentOptions:
    """Provider route and request limits fixed for one Agent."""

    provider: str
    model: str
    max_tokens: int | None = None

    def __post_init__(self) -> None:
        if not self.provider or not self.model:
            raise ValueError("agent provider and model must be non-empty")
        if self.max_tokens is not None and (
            isinstance(self.max_tokens, bool)
            or not isinstance(self.max_tokens, int)
            or self.max_tokens <= 0
        ):
            raise ValueError("agent max_tokens must be a positive integer")


class Agent:
    """One active inbox and Session controlled by the Agent Loop."""

    def __init__(
        self,
        agent_id: AgentId,
        session: Session,
        options: AgentOptions,
        wake: Callable[[Agent], None],
        cancel: Callable[[Agent], None],
    ) -> None:
        self.id = agent_id
        self.session = session
        self.options = options
        self.status = AgentStatus.IDLE
        self.last_error: LlmFailure | None = None
        self._inbox: list[Message] = []
        self._wake = wake
        self._cancel = cancel
        self._idle = asyncio.Event()
        self._idle.set()

    @property
    def inbox(self) -> tuple[Message, ...]:
        """Return pending next-turn messages without exposing mutation."""

        return tuple(self._inbox)

    def followup(self, message: Message) -> None:
        """Queue one user-role message and wake the driver."""

        if message.role != "user":
            raise TypeError("agent followup requires a user-role message")
        self._inbox.append(message)
        self._wake(self)

    def cancel(self) -> None:
        """Drop queued work and cancel the active turn, if any."""

        self._inbox.clear()
        self._cancel(self)

    async def when_idle(self) -> None:
        """Wait until no active driver task or cleanup remains."""

        await self._idle.wait()

    def _claim(self) -> tuple[Message, ...]:
        messages = tuple(self._inbox)
        self._inbox.clear()
        return messages
