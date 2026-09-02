"""Package-level smoke tests for the initialized project."""

from importlib.util import find_spec

from dsh import __version__
from dsh.cordis import Context
from dsh.core.model.llm import plugin as llm_plugin
from dsh.core.runtime.agent import plugin as agent_plugin
from dsh.core.runtime.agent_loop import plugin as agent_loop_plugin
from dsh.core.runtime.session import plugin as session_plugin
from dsh.core.runtime.system_prompt import plugin as system_prompt_plugin
from dsh.plugins.providers.model.llm_scripted import plugin as llm_scripted_plugin


def test_package_version() -> None:
    assert __version__ == "0.1.0"


def test_three_zone_plugin_entrypoints_are_importable_without_old_shims() -> None:
    assert all(
        entry is not None
        for entry in (
            llm_plugin,
            agent_plugin,
            agent_loop_plugin,
            session_plugin,
            system_prompt_plugin,
            llm_scripted_plugin,
        )
    )
    assert find_spec("dsh.llm") is None
    assert find_spec("dsh.agent") is None


async def test_minimal_plugin_lifecycle() -> None:
    context = Context()

    def plugin(ctx: Context, config: object) -> None:
        ctx.provide("answer", 42)

    fiber = context.plugin(plugin)
    await fiber.wait()

    assert context.answer == 42

    await context.aclose()
