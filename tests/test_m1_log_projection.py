"""M1 assembled path: scripted LLM output is logged and projected."""

from typing import cast

from dsh.cordis import Context
from dsh.llm import BlockAssembler, GenerateRequest, LlmRuntime, TextBlock, create_user_message
from dsh.llm_scripted import plugin as scripted_plugin
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
from dsh.session import plugin as session_plugin


async def test_scripted_response_round_trips_through_session_log() -> None:
    context = Context()
    llm_fiber = context.plugin(LlmRuntime)
    session_fiber = context.plugin(session_plugin)
    scripted_fiber = context.plugin(scripted_plugin, {"responses": ["hello from model"]})
    await llm_fiber.wait()
    await session_fiber.wait()
    await scripted_fiber.wait()
    llm = cast(LlmRuntime, context.get("llm"))
    sessions = cast(SessionStore, context.get("sessions"))
    session = sessions.create(SessionId("m1"))

    user = create_user_message((TextBlock("hello"),))
    session.append("turn/start", TurnStartData(1))
    session.append("step/start", StepStartData(1, 1))
    session.append("user/message", user)

    request = GenerateRequest("scripted", "test-model", session.derive_messages())
    assembler = BlockAssembler()
    async for chunk in llm.stream(request):
        session.append("assistant/chunk", AssistantChunkData(1, 1, chunk))
        assembler.push(chunk)
    assistant = assembler.message(provider=request.provider, model=request.model)
    session.append("assistant/message", AssistantMessageData(1, 1, assistant, assembler.usage))
    session.append("step/end", StepEndData(1, 1))
    session.append("turn/end", TurnEndData(1, "completed"))

    projected = session.derive_messages()
    assert projected == (user, assistant)
    assert projected[1].content == (TextBlock("hello from model"),)
    next_request = GenerateRequest("scripted", "test-model", projected)
    assert next_request.messages == session.derive_messages()
    assert [event.type for event in session.events] == [
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
