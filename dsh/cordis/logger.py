"""Named logging with lifecycle-owned exporters."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import TYPE_CHECKING, Protocol

from loguru import logger as loguru_logger

from .effect import Effect

if TYPE_CHECKING:
    from .context import Context


class LogLevel(IntEnum):
    """Logger severity threshold."""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40


@dataclass(frozen=True, slots=True)
class LogMessage:
    """Structured message delivered to exporters."""

    timestamp: float
    level: LogLevel
    logger: str
    template: str
    args: tuple[object, ...]
    exception: BaseException | None = None

    @property
    def text(self) -> str:
        """Format the message only when an exporter requests it."""

        return self.template % self.args if self.args else self.template


class Exporter(Protocol):
    """Receive structured log messages."""

    def export(self, message: LogMessage) -> None:
        """Export one message."""


class Logger:
    """A lightweight named view over LoggerService."""

    def __init__(self, service: LoggerService, name: str) -> None:
        self.service = service
        self.name = name

    def debug(self, template: str, *args: object) -> None:
        self.service.write(self.name, LogLevel.DEBUG, template, args)

    def info(self, template: str, *args: object) -> None:
        self.service.write(self.name, LogLevel.INFO, template, args)

    def warning(self, template: str, *args: object) -> None:
        self.service.write(self.name, LogLevel.WARNING, template, args)

    warn = warning

    def error(
        self,
        template: str | BaseException,
        *args: object,
        exception: BaseException | None = None,
    ) -> None:
        if isinstance(template, BaseException):
            exception = template
            template = str(template)
        self.service.write(self.name, LogLevel.ERROR, template, args, exception)


class LoggerService:
    """Create named loggers and fan messages out to exporters."""

    def __init__(self, root: Context) -> None:
        self.root = root
        self._exporters: list[Exporter] = []
        self._levels: dict[str, LogLevel] = {"": LogLevel.INFO}
        self._loguru_effect: Effect | None = None
        if _env_enabled("DSH_CORDIS_LOG"):
            raw_level = os.getenv("DSH_CORDIS_LOG_LEVEL", "DEBUG").upper()
            try:
                level = LogLevel[raw_level]
            except KeyError:
                level = LogLevel.DEBUG
            self.enable_loguru(level)

    def __call__(self, name: str = "app") -> Logger:
        return Logger(self, name)

    def set_level(self, name: str, level: LogLevel) -> None:
        """Set a threshold for a logger namespace."""

        self._levels[name] = level

    @property
    def diagnostics_enabled(self) -> bool:
        """Whether the built-in Loguru diagnostic exporter is active."""

        return self._loguru_effect is not None and not self._loguru_effect.disposed

    def enable_loguru(self, level: LogLevel = LogLevel.DEBUG) -> Effect:
        """Enable lifecycle-owned Cordis diagnostics through Loguru."""

        self.set_level("cordis", level)
        if self._loguru_effect is not None and not self._loguru_effect.disposed:
            return self._loguru_effect
        exporter = LoguruExporter()
        effect = self.exporter(self.root, exporter)
        self._loguru_effect = effect
        self("cordis.logger").info("diagnostics enabled level=%s", level.name)
        return effect

    async def disable_loguru(self) -> None:
        """Disable the built-in Loguru exporter and wait for its removal."""

        effect, self._loguru_effect = self._loguru_effect, None
        if effect is not None:
            await effect.dispose()

    def level(self, name: str) -> LogLevel:
        """Resolve the nearest namespace threshold."""

        matches = (
            prefix
            for prefix in self._levels
            if not prefix or name == prefix or name.startswith(prefix + ".")
        )
        prefix = max(matches, key=len)
        return self._levels[prefix]

    def exporter(self, context: Context, exporter: Exporter) -> Effect:
        """Register an exporter owned by the calling Context."""

        def setup() -> object:
            self._exporters.append(exporter)

            def cleanup() -> None:
                try:
                    self._exporters.remove(exporter)
                except ValueError:
                    pass

            return cleanup

        return context.fiber.effects.install_sync(setup, "ctx.logger.exporter()")

    def write(
        self,
        name: str,
        level: LogLevel,
        template: str,
        args: tuple[object, ...],
        exception: BaseException | None = None,
    ) -> None:
        """Deliver a structured message when its threshold is enabled."""

        if level < self.level(name):
            return
        message = LogMessage(time.time(), level, name, template, args, exception)
        for exporter in tuple(self._exporters):
            exporter.export(message)


class LoguruExporter:
    """Forward structured Cordis messages to Loguru without changing global sinks."""

    def export(self, message: LogMessage) -> None:
        bound = loguru_logger.bind(cordis_logger=message.logger)
        bound.opt(exception=message.exception).log(
            message.level.name, f"[{message.logger}] {message.text}"
        )


def _env_enabled(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}
