"""Process-wide Loguru logger used by Cordis internals."""

from __future__ import annotations

import os

from loguru import logger as _loguru_logger

_CORDIS_NAMESPACE = "dsh.cordis"
_enabled = False

# All Cordis modules import this singleton and use normal logger.info(...) calls.
logger = _loguru_logger.bind(subsystem="cordis")


def set_cordis_logging(enabled: bool) -> None:
    """Enable or disable all Loguru records originating from ``dsh.cordis``."""

    global _enabled
    _enabled = enabled
    if enabled:
        _loguru_logger.enable(_CORDIS_NAMESPACE)
    else:
        _loguru_logger.disable(_CORDIS_NAMESPACE)


def is_cordis_logging_enabled() -> bool:
    """Return the current process-wide Cordis logging switch."""

    return _enabled


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


set_cordis_logging(_env_enabled("DSH_CORDIS_LOG"))
