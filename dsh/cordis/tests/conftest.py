"""Shared Cordis test fixtures."""

from collections.abc import AsyncIterator

import pytest

from dsh.cordis import Context


@pytest.fixture
async def context() -> AsyncIterator[Context]:
    runtime = Context()
    try:
        yield runtime
    finally:
        await runtime.aclose()
