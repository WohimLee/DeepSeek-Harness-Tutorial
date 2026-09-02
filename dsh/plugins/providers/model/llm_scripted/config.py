"""Configuration for the deterministic scripted provider."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Self, cast


@dataclass(frozen=True, slots=True)
class Config:
    """Provider route and ordered text responses."""

    responses: tuple[str, ...]
    provider: str = "scripted"

    @classmethod
    def validate(cls, value: object) -> Self:
        if not isinstance(value, Mapping):
            raise TypeError("config must be a mapping")
        raw = cast(Mapping[object, object], value)
        provider = raw.get("provider", "scripted")
        responses = raw.get("responses")
        if not isinstance(provider, str) or not provider:
            raise TypeError("provider must be a non-empty string")
        if not isinstance(responses, list | tuple) or not all(
            isinstance(response, str) for response in responses
        ):
            raise TypeError("responses must be an array of strings")
        return cls(tuple(cast(list[str] | tuple[str, ...], responses)), provider)
