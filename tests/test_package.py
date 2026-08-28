"""Package-level smoke tests for the initialized project."""

from dsh import __version__
from dsh.cordis import Context


def test_package_version() -> None:
    assert __version__ == "0.1.0"


async def test_minimal_plugin_lifecycle() -> None:
    context = Context()

    def plugin(ctx: Context, config: object) -> None:
        ctx.provide("answer", 42)

    fiber = context.plugin(plugin)
    await fiber.wait()

    assert context.answer == 42

    await context.aclose()
