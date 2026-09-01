"""Typed construction helper for object-style Cordis plugins."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .context import Context
from .effect import EffectResult


@dataclass(frozen=True, slots=True)
class PluginDefinition[ConfigT]:
    """Explicit plugin metadata with a config-aware activation callback."""

    name: str
    apply_callback: Callable[[Context, ConfigT], EffectResult]
    inject: tuple[str, ...] | Mapping[str, object | None] = ()
    Config: object | None = None

    def apply(self, context: Context, config: ConfigT) -> EffectResult:
        """Activate the callback after Cordis has resolved metadata and config."""

        return self.apply_callback(context, config)


def define_plugin[ConfigT](
    name: str,
    apply: Callable[[Context, ConfigT], EffectResult],
    *,
    inject: tuple[str, ...] | Mapping[str, object | None] = (),
    config: object | None = None,
) -> PluginDefinition[ConfigT]:
    """Build a typed object-style plugin without dynamic attributes."""

    if not name:
        raise ValueError("plugin name must be non-empty")
    return PluginDefinition(name, apply, inject, config)
