"""Python implementation of the Cordis plugin runtime."""

from .config import ConfigValidator, ValidationError
from .context import Context
from .effect import Effect, EffectMeta, EffectScope
from .errors import CordisError, CordisErrorCode
from .events import EventsService, is_bailed
from .fiber import Fiber, FiberState
from .logger import is_cordis_logging_enabled, logger, set_cordis_logging
from .model import inject
from .plugin import PluginDefinition, define_plugin
from .service import Service
from .typing import PluginContext, PluginFunction, PluginObject

__version__ = "0.1.0"

__all__ = [
    "ConfigValidator",
    "Context",
    "CordisError",
    "CordisErrorCode",
    "Effect",
    "EffectMeta",
    "EffectScope",
    "EventsService",
    "Fiber",
    "FiberState",
    "PluginContext",
    "PluginDefinition",
    "PluginFunction",
    "PluginObject",
    "Service",
    "ValidationError",
    "__version__",
    "define_plugin",
    "inject",
    "is_bailed",
    "is_cordis_logging_enabled",
    "logger",
    "set_cordis_logging",
]
