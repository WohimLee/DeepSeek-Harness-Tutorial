"""In-memory Session and lifecycle-owned SessionStore plugin."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import cast
from uuid import uuid4

from dsh.cordis import Context, Service
from dsh.core.model.llm import Message, ModelSource, ToolResultBlock, ToolSource

from .models import (
    AssistantChunkData,
    AssistantMessageData,
    EventData,
    EventType,
    SessionEvent,
    SessionId,
    StepEndData,
    StepStartData,
    ToolCallData,
    ToolResultData,
    TurnEndData,
    TurnStartData,
)

_EVENT_DATA_TYPES: dict[EventType, type[object]] = {
    "turn/start": TurnStartData,
    "turn/end": TurnEndData,
    "step/start": StepStartData,
    "step/end": StepEndData,
    "user/message": Message,
    "assistant/chunk": AssistantChunkData,
    "assistant/message": AssistantMessageData,
    "tool/call": ToolCallData,
    "tool/result": ToolResultData,
}


class Session:
    """One append-only event log whose model history is a projection."""

    def __init__(
        self,
        session_id: SessionId,
        publish: Callable[[Session, SessionEvent], None] | None = None,
    ) -> None:
        self.id = session_id
        self._events: list[SessionEvent] = []
        self._publish = publish

    @property
    def events(self) -> tuple[SessionEvent, ...]:
        """Return a stable snapshot of the event log."""

        return tuple(self._events)

    def append(self, event_type: EventType, data: EventData) -> SessionEvent:
        """Validate and append one core event with a contiguous sequence."""

        expected = _EVENT_DATA_TYPES[event_type]
        if not isinstance(data, expected):
            raise TypeError(f"{event_type} data must be {expected.__name__}")
        self._validate_message_event(event_type, data)
        event = SessionEvent(event_type, len(self._events), time.time_ns() // 1_000_000, data)
        self._events.append(event)
        if self._publish is not None:
            self._publish(self, event)
        return event

    @staticmethod
    def _validate_message_event(event_type: EventType, data: EventData) -> None:
        if event_type == "user/message":
            message = cast(Message, data)
            if message.role != "user":
                raise TypeError('user/message must have role "user"')
            return
        if event_type == "assistant/message":
            message = cast(AssistantMessageData, data).message
            if message.role != "assistant" or not isinstance(message.source, ModelSource):
                raise TypeError("assistant/message must have assistant role and model source")
            return
        if event_type == "tool/result":
            message = cast(ToolResultData, data).message
            valid = (
                message.role == "user"
                and isinstance(message.source, ToolSource)
                and len(message.content) == 1
                and isinstance(message.content[0], ToolResultBlock)
                and message.content[0].tool_call_id == message.source.call_id
            )
            if not valid:
                raise TypeError("tool/result must contain one correlated tool-result message")

    def derive_messages(self) -> tuple[Message, ...]:
        """Project model-visible messages; raw chunks and brackets remain log-only."""

        messages: list[Message] = []
        for event in self._events:
            if event.type == "user/message":
                messages.append(cast(Message, event.data))
            elif event.type == "assistant/message":
                messages.append(cast(AssistantMessageData, event.data).message)
            elif event.type == "tool/result":
                messages.append(cast(ToolResultData, event.data).message)
        return tuple(messages)


class SessionStore(Service):
    """Own in-memory sessions for the current Harness process."""

    name = "session"
    provide = "sessions"

    def __init__(self, context: Context, config: object = None) -> None:
        super().__init__(context)
        self._sessions: dict[SessionId, Session] = {}

    def create(self, session_id: SessionId | None = None) -> Session:
        """Create and publish one empty session."""

        resolved = session_id or SessionId(str(uuid4()))
        if resolved in self._sessions:
            raise ValueError(f"session {resolved!r} already exists")
        session = Session(
            resolved,
            lambda current, event: self.context.emit("session/event", current, event),
        )
        self._sessions[resolved] = session
        return session

    def get_session(self, session_id: SessionId) -> Session:
        """Return an existing session or raise KeyError."""

        return self._sessions[session_id]

    def list_sessions(self) -> tuple[Session, ...]:
        """List sessions in creation order."""

        return tuple(self._sessions.values())


plugin = SessionStore
