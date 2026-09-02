"""Append-only session log contracts."""

import pytest

from dsh.core.model.llm import (
    CallId,
    TextBlock,
    TextDelta,
    ToolCallBlock,
    create_assistant_message,
    create_tool_result_message,
    create_user_message,
)
from dsh.core.runtime.session import (
    AssistantChunkData,
    AssistantMessageData,
    Session,
    SessionId,
    ToolResultData,
    TurnEndData,
    TurnStartData,
)


def test_session_derives_messages_only_from_surface_events() -> None:
    session = Session(SessionId("session-1"))
    user = create_user_message((TextBlock("hello"),))
    assistant = create_assistant_message(
        (TextBlock("checking"), ToolCallBlock(CallId("call-1"), "echo", "{}")),
        provider="scripted",
        model="test",
    )
    tool = create_tool_result_message(CallId("call-1"), (TextBlock("ok"),))

    session.append("turn/start", TurnStartData(1))
    session.append("user/message", user)
    session.append("assistant/chunk", AssistantChunkData(1, 1, TextDelta(0, "checking")))
    session.append("assistant/message", AssistantMessageData(1, 1, assistant))
    session.append("tool/result", ToolResultData(1, 1, tool))
    session.append("turn/end", TurnEndData(1, "completed"))

    assert session.derive_messages() == (user, assistant, tool)
    assert [event.seq for event in session.events] == list(range(6))


def test_session_rejects_mismatched_event_payload() -> None:
    session = Session(SessionId("session-1"))

    with pytest.raises(TypeError, match="turn/start data must be TurnStartData"):
        session.append("turn/start", TurnEndData(1, "completed"))


def test_session_rejects_message_role_for_wrong_event() -> None:
    session = Session(SessionId("session-1"))
    assistant = create_assistant_message(
        (TextBlock("not user input"),),
        provider="scripted",
        model="test",
    )

    with pytest.raises(TypeError, match='user/message must have role "user"'):
        session.append("user/message", assistant)
