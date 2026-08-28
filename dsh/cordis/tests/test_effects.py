"""Effect rollback, ordering, and cancellation contracts."""

import asyncio
from collections.abc import AsyncIterator

import pytest

from dsh.cordis import EffectScope


async def test_failed_async_setup_rolls_back_collected_cleanups() -> None:
    scope = EffectScope()
    calls: list[str] = []

    async def resources() -> AsyncIterator[object]:
        calls.append("setup")
        yield lambda: calls.append("cleanup")
        raise RuntimeError("setup failed")

    with pytest.raises(RuntimeError, match="setup failed"):
        await scope.install(resources, "failing setup")

    assert calls == ["setup", "cleanup"]
    assert scope.effects == ()


async def test_scope_closes_effects_and_cleanups_in_reverse_order() -> None:
    scope = EffectScope()
    calls: list[str] = []

    scope.install_sync(lambda: lambda: calls.append("first"), "first")
    scope.install_sync(
        lambda: [lambda: calls.append("second-a"), lambda: calls.append("second-b")],
        "second",
    )

    await scope.close()
    await scope.close()

    assert calls == ["second-b", "second-a", "first"]


async def test_cancelled_dispose_waiter_does_not_cancel_cleanup() -> None:
    scope = EffectScope()
    cleanup_started = asyncio.Event()
    allow_cleanup = asyncio.Event()
    cleanup_finished = asyncio.Event()

    async def cleanup() -> None:
        cleanup_started.set()
        await allow_cleanup.wait()
        cleanup_finished.set()

    scope.install_sync(lambda: cleanup, "slow cleanup")

    waiter = asyncio.create_task(scope.close())
    await cleanup_started.wait()
    waiter.cancel()
    with pytest.raises(asyncio.CancelledError):
        await waiter

    allow_cleanup.set()
    await scope.close()

    assert cleanup_finished.is_set()
