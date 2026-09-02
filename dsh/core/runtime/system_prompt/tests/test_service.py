"""System Prompt registry, ordering, waterfall, and lifecycle contracts."""

from typing import cast

from dsh.cordis import Context
from dsh.core.runtime.system_prompt import PromptAssembly, PromptSection, SystemPrompt, plugin


async def test_sections_are_ordered_and_removed_with_owner() -> None:
    context = Context()
    prompt_fiber = context.plugin(plugin, {"persona": "base"})
    await prompt_fiber.wait()
    prompt = cast(SystemPrompt, context.get("systemPrompt"))

    def contributor(ctx: Context, _config: object) -> None:
        service = cast(SystemPrompt, ctx.get("systemPrompt"))
        service.section(PromptSection("later", "later", 20))
        service.section(PromptSection("earlier", "earlier", 10))

    contributor_fiber = context.plugin(contributor)
    await contributor_fiber.wait()
    assert (await prompt.assemble()).text == "base\n\nearlier\n\nlater"

    await contributor_fiber.dispose()
    assert (await prompt.assemble()).text == "base"
    await context.aclose()


async def test_assemble_waterfall_can_replace_the_result() -> None:
    context = Context()
    fiber = context.plugin(plugin)
    await fiber.wait()
    prompt = cast(SystemPrompt, context.get("systemPrompt"))

    async def replace(
        _assembly: PromptAssembly,
        _context: object,
        _next: object,
    ) -> PromptAssembly:
        return PromptAssembly((PromptSection("replacement", "replaced"),))

    context.on("system-prompt/assemble", replace)
    assert (await prompt.assemble()).text == "replaced"
    await context.aclose()
