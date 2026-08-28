"""Plugins resolved by declarative Loader contract tests."""

from dsh.cordis import Context

events: list[str] = []


def parent_plugin(ctx: Context, config: object) -> object:
    events.append("parent:start")
    return lambda: events.append("parent:stop")


def child_plugin(ctx: Context, config: object) -> object:
    events.append("child:start")
    return lambda: events.append("child:stop")


class PositiveIntegerConfig:
    """Normalize one positive integer fixture config."""

    @staticmethod
    def validate(value: object) -> int:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise TypeError("config must be a positive integer")
        return value


class ConfiguredPlugin:
    name = "configured"
    Config = PositiveIntegerConfig

    def apply(self, ctx: Context, config: int) -> object:
        events.append(f"configured:start:{config}")
        return lambda: events.append(f"configured:stop:{config}")


configured_plugin = ConfiguredPlugin()
