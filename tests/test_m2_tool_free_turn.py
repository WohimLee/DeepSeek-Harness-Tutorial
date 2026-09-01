"""M2 assembled path: input reaches a streamed final response through Agent Loop."""

from typing import cast

from dsh.agent import AgentOptions
from dsh.agent import plugin as agent_plugin
from dsh.agent_loop import AgentLoop
from dsh.agent_loop import plugin as loop_plugin
from dsh.cordis import Context
from dsh.llm import TextBlock, create_user_message
from dsh.llm import plugin as llm_plugin
from dsh.llm_scripted import plugin as scripted_plugin
from dsh.session import SessionId
from dsh.session import plugin as session_plugin
from dsh.system_prompt import plugin as prompt_plugin


async def test_user_input_reaches_streamed_final_response() -> None:
    context = Context()
    fibers = [
        context.plugin(llm_plugin),
        context.plugin(session_plugin),
        context.plugin(prompt_plugin, {"persona": "Answer briefly."}),
        context.plugin(agent_plugin),
        context.plugin(scripted_plugin, {"responses": ["hello from M2"]}),
    ]
    for fiber in fibers:
        await fiber.wait()
    loop_fiber = context.plugin(loop_plugin)
    await loop_fiber.wait()
    loop = cast(AgentLoop, context.get("agentLoop"))
    agent = loop.create(SessionId("m2"), AgentOptions("scripted", "test-model"))

    agent.followup(create_user_message((TextBlock("hello"),)))
    await agent.when_idle()

    messages = agent.session.derive_messages()
    assert [message.content for message in messages] == [
        (TextBlock("hello"),),
        (TextBlock("hello from M2"),),
    ]
    assert agent.session.events[-1].type == "turn/end"
    assert agent.session.events[-1].data.reason == "completed"  # type: ignore[union-attr]
    await context.aclose()
