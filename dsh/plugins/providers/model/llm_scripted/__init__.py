"""Deterministic keyless LLM provider for tests and examples."""

from .config import Config
from .plugin import ScriptedAdapter, ScriptedPlugin, plugin

__all__ = ["Config", "ScriptedAdapter", "ScriptedPlugin", "plugin"]
