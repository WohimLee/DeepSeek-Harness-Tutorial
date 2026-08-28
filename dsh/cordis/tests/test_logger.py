"""Cordis diagnostic logging switches."""

from __future__ import annotations

from typing import Self

from pytest import MonkeyPatch

from dsh.cordis import Context, LogLevel


class FakeLoguru:
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def bind(self, **kwargs: object) -> Self:
        return self

    def opt(self, **kwargs: object) -> Self:
        return self

    def log(self, level: str, text: str) -> None:
        self.records.append((level, text))


async def test_loguru_diagnostics_are_disabled_by_default(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("DSH_CORDIS_LOG", raising=False)
    context = Context()

    assert not context.logger.diagnostics_enabled
    await context.aclose()


async def test_loguru_diagnostics_can_be_enabled_and_disabled(monkeypatch: MonkeyPatch) -> None:
    fake = FakeLoguru()
    monkeypatch.setattr("dsh.cordis.logger.loguru_logger", fake)
    monkeypatch.setenv("DSH_CORDIS_LOG", "1")
    monkeypatch.setenv("DSH_CORDIS_LOG_LEVEL", "DEBUG")

    context = Context()
    context.logger("cordis.test").debug("fiber=%s", 7)

    assert context.logger.diagnostics_enabled
    assert ("DEBUG", "[cordis.test] fiber=7") in fake.records

    await context.logger.disable_loguru()
    context.logger("cordis.test").error("after disable")
    assert ("ERROR", "[cordis.test] after disable") not in fake.records
    await context.aclose()


async def test_loguru_runtime_enable_respects_level(monkeypatch: MonkeyPatch) -> None:
    fake = FakeLoguru()
    monkeypatch.setattr("dsh.cordis.logger.loguru_logger", fake)
    monkeypatch.delenv("DSH_CORDIS_LOG", raising=False)
    context = Context()

    context.logger.enable_loguru(LogLevel.WARNING)
    context.logger("cordis.test").info("hidden")
    context.logger("cordis.test").warning("shown")

    assert ("INFO", "[cordis.test] hidden") not in fake.records
    assert ("WARNING", "[cordis.test] shown") in fake.records
    await context.aclose()
