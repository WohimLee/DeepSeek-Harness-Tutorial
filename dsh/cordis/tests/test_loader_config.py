"""Configuration parsing and composition security contracts."""

from pathlib import Path

import pytest

from dsh.cordis.loader import ConfigComposer, LoaderError, YamlConfigParser


def test_yaml_parser_builds_children_and_interpolates_environment() -> None:
    parser = YamlConfigParser()
    source = Path("cordis.yaml")

    entries = parser.loads(
        """
plugins:
  - id: parent
    module: example:parent
    config:
      token: ${TOKEN}
    plugins:
      - id: child
        module: example:child
        inject:
          tools:
            mode: strict
""",
        source,
        env={"TOKEN": "secret-value"},
    )

    assert entries[0].id == "parent"
    assert entries[0].config == {"token": "secret-value"}
    assert entries[0].children[0].id == "child"
    assert entries[0].children[0].inject == {"tools": {"mode": "strict"}}


def test_yaml_parser_rejects_python_object_tags() -> None:
    parser = YamlConfigParser()

    with pytest.raises(LoaderError, match="invalid YAML"):
        parser.loads(
            "plugins: !!python/object/apply:os.system [['echo unsafe']]",
            Path("unsafe.yaml"),
        )


def test_composer_applies_nested_overlay_to_included_entry(tmp_path: Path) -> None:
    base = tmp_path / "base.toml"
    root = tmp_path / "root.toml"
    base.write_text(
        """
[[plugins]]
id = "model"
module = "example:model"
config = { model = "base", limits = { tokens = 100, calls = 2 } }
"""
    )
    root.write_text(
        """
include = "base.toml"

[overlays.model.config]
model = "override"
limits = { tokens = 200 }
"""
    )

    entries = ConfigComposer().load(root)

    assert entries[0].config == {
        "model": "override",
        "limits": {"tokens": 200, "calls": 2},
    }


def test_composer_rejects_include_cycle(tmp_path: Path) -> None:
    first = tmp_path / "first.toml"
    second = tmp_path / "second.toml"
    first.write_text('include = "second.toml"\n')
    second.write_text('include = "first.toml"\n')

    with pytest.raises(LoaderError, match="include cycle detected"):
        ConfigComposer().load(first)
