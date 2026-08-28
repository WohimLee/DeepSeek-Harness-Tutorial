"""Declarative Loader tree ownership contracts."""

from pathlib import Path

import pytest

from dsh.cordis import Context, FiberState
from dsh.cordis.loader import Loader, LoaderError, ModuleResolver, ParsedEntry, SourceLocation
from dsh.cordis.tests.fixtures import loader_plugins


def _entry(
    entry_id: str,
    attribute: str,
    *,
    children: tuple[ParsedEntry, ...] = (),
    disabled: bool = False,
    config: object = None,
) -> ParsedEntry:
    return ParsedEntry(
        id=entry_id,
        module=f"dsh.cordis.tests.fixtures.loader_plugins:{attribute}",
        config=config,
        location=SourceLocation(Path("cordis.test.yaml")),
        disabled=disabled,
        children=children,
    )


async def test_loader_mounts_and_disposes_entry_tree(context: Context) -> None:
    loader_plugins.events.clear()
    loader = Loader(context, ModuleResolver(allowed_packages=("dsh",)))
    child = _entry("child", "child_plugin")
    parent = _entry("parent", "parent_plugin", children=(child,))

    roots = await loader.mount((parent,))

    assert loader_plugins.events == ["parent:start", "child:start"]
    assert roots[0].children[0].parent is roots[0]
    assert roots[0].fiber is not None
    assert roots[0].fiber.state is FiberState.ACTIVE
    assert roots[0].children[0].fiber is not None
    assert roots[0].children[0].fiber.state is FiberState.ACTIVE

    await loader.close()

    assert loader_plugins.events == [
        "parent:start",
        "child:start",
        "child:stop",
        "parent:stop",
    ]


async def test_disabled_parent_suppresses_its_subtree(context: Context) -> None:
    loader_plugins.events.clear()
    loader = Loader(context, ModuleResolver(allowed_packages=("dsh",)))
    child = _entry("child", "child_plugin")
    parent = _entry("parent", "parent_plugin", children=(child,), disabled=True)

    roots = await loader.mount((parent,))

    assert loader_plugins.events == []
    assert roots[0].fiber is None
    assert roots[0].children == []

    await loader.close()


async def test_leaf_config_update_restarts_plugin_atomically(context: Context) -> None:
    loader_plugins.events.clear()
    loader = Loader(context, ModuleResolver(allowed_packages=("dsh",)))
    initial = _entry("configured", "configured_plugin", config=1)
    changed = _entry("configured", "configured_plugin", config=2)

    roots = await loader.mount((initial,))
    await loader.update((changed,))

    assert loader_plugins.events == [
        "configured:start:1",
        "configured:stop:1",
        "configured:start:2",
    ]
    assert roots[0].version == 1
    assert roots[0].parsed.config == 2

    await loader.close()
    assert loader_plugins.events[-1] == "configured:stop:2"


async def test_invalid_config_update_keeps_previous_activation(context: Context) -> None:
    loader_plugins.events.clear()
    loader = Loader(context, ModuleResolver(allowed_packages=("dsh",)))
    initial = _entry("configured", "configured_plugin", config=1)
    invalid = _entry("configured", "configured_plugin", config=0)

    roots = await loader.mount((initial,))
    with pytest.raises(LoaderError, match="failed to update entry configuration"):
        await loader.update((invalid,))

    assert loader_plugins.events == ["configured:start:1"]
    assert roots[0].parsed.config == 1
    assert roots[0].fiber is not None
    assert roots[0].fiber.state is FiberState.ACTIVE

    await loader.close()
