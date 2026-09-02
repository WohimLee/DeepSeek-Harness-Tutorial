"""Validated System Prompt plugin configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self


@dataclass(frozen=True, slots=True)
class Config:
    """Static deployment persona contributed at the first prompt position."""

    persona: str = ""

    @classmethod
    def validate(cls, value: object) -> Self:
        if value is None:
            return cls()
        if not isinstance(value, dict):
            raise TypeError("system-prompt config must be a mapping")
        unknown = set(value) - {"persona"}
        if unknown:
            raise TypeError(f"unknown system-prompt config field: {min(unknown)!r}")
        persona = value.get("persona", "")
        if not isinstance(persona, str):
            raise TypeError("system-prompt persona must be a string")
        return cls(persona)
