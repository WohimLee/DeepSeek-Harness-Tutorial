"""Fiber dependency and parent-child ownership contracts."""

import asyncio
from dataclasses import dataclass

import pytest

from dsh.cordis import Context, Fiber, FiberState


@dataclass(frozen=True, slots=True)
class ValueProvider:
    value: str
    name = "value-provider"

    def apply(self, ctx: Context, config: object) -> None:
        ctx.provide("value", self.value)


class ValueConsumer:
    name = "value-consumer"
    inject = ("value",)

    def __init__(self, calls: list[str]) -> None:
        self.calls = calls

    def apply(self, ctx: Context, config: object) -> object:
        value = ctx.get("value")
        self.calls.append(f"start:{value}")
        return lambda: self.calls.append(f"stop:{value}")


async def _settle(fiber: Fiber) -> None:
    await asyncio.sleep(0)
    await fiber.wait()


def _assert_state(fiber: Fiber, expected: FiberState) -> None:
    assert fiber.state is expected


async def test_consumer_tracks_provider_appearance_removal_and_replacement(
    context: Context,
) -> None:
    calls: list[str] = []
    consumer = context.plugin(ValueConsumer(calls))
    await consumer.wait()
    _assert_state(consumer, FiberState.PENDING)

    first = context.plugin(ValueProvider("first"))
    await first.wait()
    await _settle(consumer)
    _assert_state(consumer, FiberState.ACTIVE)
    assert calls == ["start:first"]

    await first.dispose()
    await _settle(consumer)
    _assert_state(consumer, FiberState.PENDING)
    assert calls == ["start:first", "stop:first"]

    second = context.plugin(ValueProvider("second"))
    await second.wait()
    await _settle(consumer)
    _assert_state(consumer, FiberState.ACTIVE)
    assert calls == ["start:first", "stop:first", "start:second"]


async def test_parent_disposal_recursively_disposes_child(context: Context) -> None:
    calls: list[str] = []
    children: list[Fiber] = []

    def child_plugin(ctx: Context, config: object) -> object:
        calls.append("child:start")
        return lambda: calls.append("child:stop")

    def parent_plugin(ctx: Context, config: object) -> object:
        calls.append("parent:start")
        children.append(ctx.plugin(child_plugin))
        return lambda: calls.append("parent:stop")

    parent = context.plugin(parent_plugin)
    await parent.wait()
    await children[0].wait()

    await parent.dispose()

    _assert_state(parent, FiberState.DISPOSED)
    _assert_state(children[0], FiberState.DISPOSED)
    assert calls == ["parent:start", "child:start", "parent:stop", "child:stop"]


async def test_parent_activation_failure_rolls_back_child_and_effects(context: Context) -> None:
    calls: list[str] = []
    children: list[Fiber] = []

    def child_plugin(ctx: Context, config: object) -> object:
        calls.append("child:start")
        return lambda: calls.append("child:stop")

    def parent_plugin(ctx: Context, config: object) -> None:
        ctx.effect(lambda: lambda: calls.append("parent:cleanup"), "parent resource")
        children.append(ctx.plugin(child_plugin))
        raise RuntimeError("parent failed")

    parent = context.plugin(parent_plugin)
    with pytest.raises(RuntimeError, match="parent failed"):
        await parent.wait()

    await children[0].wait()

    _assert_state(parent, FiberState.FAILED)
    _assert_state(children[0], FiberState.DISPOSED)
    assert "parent:cleanup" in calls
    assert "child:stop" in calls or "child:start" not in calls
