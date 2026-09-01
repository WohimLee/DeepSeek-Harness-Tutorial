"""Values exchanged by prompt contributors and one assembly call."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AssembleContext:
    """Per-request prompt assembly metadata kept intentionally small in M2."""

    agent_id: str | None = None


@dataclass(frozen=True, slots=True)
class PromptSection:
    """One uniquely named, ordered system-prompt contribution."""

    name: str
    text: str
    order: int = 0


@dataclass(frozen=True, slots=True)
class PromptAssembly:
    """Resolved prompt sections and their canonical rendered text."""

    sections: tuple[PromptSection, ...]

    @property
    def text(self) -> str:
        """Join non-empty sections with stable paragraph separators."""

        return "\n\n".join(section.text for section in self.sections if section.text)
