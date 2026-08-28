"""Stable provider-neutral LLM failures."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LlmFailure:
    """Serializable provider or transport failure facts."""

    message: str
    code: str
    status: int | None = None
    retry_after_ms: int | None = None
    request_id: str | None = None


class LlmError(RuntimeError):
    """LLM domain error with a stable routing code."""

    def __init__(self, message: str, code: str, *, cause: BaseException | None = None) -> None:
        self.code = code
        self.cause = cause
        super().__init__(message)

    def failure(self) -> LlmFailure:
        """Return the durable failure representation."""

        return LlmFailure(message=str(self), code=self.code)


def failure_from_exception(error: BaseException) -> LlmFailure:
    """Preserve stable LLM codes and classify unknown adapter failures."""

    if isinstance(error, LlmError):
        return error.failure()
    return LlmFailure(message=str(error) or type(error).__name__, code="UNKNOWN")
