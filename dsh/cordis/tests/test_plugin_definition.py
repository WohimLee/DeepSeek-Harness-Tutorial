"""Typed object-plugin construction contracts."""

from dataclasses import dataclass

import pytest

from dsh.cordis import Context, CordisError, define_plugin


@dataclass(frozen=True)
class _Config:
    value: int

    @classmethod
    def validate(cls, value: object) -> "_Config":
        if not isinstance(value, dict) or not isinstance(value.get("value"), int):
            raise TypeError("value must be an integer")
        return cls(value["value"])


async def test_define_plugin_preserves_typed_config_and_lifecycle() -> None:
    context = Context()

    def apply(ctx: Context, config: _Config) -> None:
        ctx.provide("answer", config.value)

    fiber = context.plugin(define_plugin("answer", apply, config=_Config), {"value": 42})
    await fiber.wait()
    assert context.get("answer") == 42

    await fiber.dispose()
    with pytest.raises(CordisError):
        context.get("answer")


def test_define_plugin_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        define_plugin("", lambda _ctx, _config: None)
