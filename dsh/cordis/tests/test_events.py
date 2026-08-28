"""Event dispatch contracts required by Harness middleware."""

from collections.abc import Awaitable, Callable

from dsh.cordis import Context

type Next = Callable[[], Awaitable[object]]


async def test_waterfall_wraps_in_registration_order(context: Context) -> None:
    calls: list[str] = []

    async def outer(value: str, next_: Next) -> object:
        calls.append(f"outer:before:{value}")
        result = await next_()
        calls.append(f"outer:after:{result}")
        return f"outer({result})"

    async def inner(value: str, next_: Next) -> object:
        calls.append(f"inner:before:{value}")
        result = await next_()
        calls.append(f"inner:after:{result}")
        return f"inner({result})"

    context.on("request", outer)
    context.on("request", inner)

    result = await context.waterfall("request", "input", next_=lambda: "terminal")

    assert result == "outer(inner(terminal))"
    assert calls == [
        "outer:before:input",
        "inner:before:input",
        "inner:after:terminal",
        "outer:after:inner(terminal)",
    ]


async def test_waterfall_listener_must_delegate_explicitly(context: Context) -> None:
    calls: list[str] = []

    async def reject(value: str, next_: Next) -> object:
        calls.append(f"reject:{value}")
        return "blocked"

    async def unreachable(value: str, next_: Next) -> object:
        calls.append(f"unreachable:{value}")
        return await next_()

    context.on("request", reject)
    context.on("request", unreachable)

    result = await context.waterfall(
        "request",
        "input",
        next_=lambda: calls.append("terminal"),
    )

    assert result == "blocked"
    assert calls == ["reject:input"]


async def test_listener_is_removed_with_owning_fiber(context: Context) -> None:
    calls: list[str] = []

    def observer_plugin(ctx: Context, config: object) -> None:
        ctx.on("observed", lambda value: calls.append(str(value)))

    fiber = context.plugin(observer_plugin)
    await fiber.wait()
    context.emit("observed", "before")

    await fiber.dispose()
    context.emit("observed", "after")

    assert calls == ["before"]
