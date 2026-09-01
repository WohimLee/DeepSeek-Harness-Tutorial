"""Lifecycle-owned registry and cooperative system-prompt assembly."""

from __future__ import annotations

from dsh.cordis import Context, Effect, Service

from .config import Config as PromptConfig
from .models import AssembleContext, PromptAssembly, PromptSection


class SystemPrompt(Service):
    """Register ordered sections and assemble them for each model request."""

    name = "system-prompt"
    provide = "systemPrompt"
    Config = PromptConfig

    def __init__(self, context: Context, config: PromptConfig) -> None:
        super().__init__(context)
        self._sections: dict[str, PromptSection] = {}
        if config.persona:
            self._register(context, PromptSection("deployment:persona", config.persona, 0))

    def section(self, section: PromptSection) -> Effect:
        """Register a unique section owned by the calling Fiber."""

        if not section.name:
            raise ValueError("prompt section name must be non-empty")
        return self._register(self.caller_context, section)

    def _register(self, owner: Context, section: PromptSection) -> Effect:
        if section.name in self._sections:
            raise ValueError(f"prompt section {section.name!r} is already registered")

        def setup() -> object:
            self._sections[section.name] = section
            self.context.emit("system-prompt/change")

            def cleanup() -> None:
                if self._sections.get(section.name) is section:
                    del self._sections[section.name]
                    self.context.emit("system-prompt/change")

            return cleanup

        return owner.effect(setup, f"systemPrompt.section({section.name!r})")

    async def assemble(self, context: AssembleContext | None = None) -> PromptAssembly:
        """Resolve canonical order, then run the authoritative waterfall."""

        assembly_context = context or AssembleContext()
        sections = tuple(sorted(self._sections.values(), key=lambda item: (item.order, item.name)))
        assembly = PromptAssembly(sections)
        result = await self.caller_context.waterfall(
            "system-prompt/assemble",
            assembly,
            assembly_context,
            next_=lambda: assembly,
        )
        if not isinstance(result, PromptAssembly):
            raise TypeError("system-prompt/assemble must return PromptAssembly")
        return result


plugin = SystemPrompt
