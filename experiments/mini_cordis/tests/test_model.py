import pytest

from experiments.mini_cordis.model import (
    PluginSpec,
    inject,
    normalize_inject,
)


def test_normalize_empty_inject() -> None:
    assert normalize_inject(None) == {}


def test_normalize_sequence_inject() -> None:
    result = normalize_inject(["database", "logger"])

    assert result == {
        "database": None,
        "logger": None,
    }


def test_normalize_tuple_inject() -> None:
    result = normalize_inject(("database", "logger"))

    assert result == {
        "database": None,
        "logger": None,
    }


def test_normalize_mapping_inject() -> None:
    source = {
        "database": None,
        "cache": {"required": False},
    }

    result = normalize_inject(source)

    assert result == source
    assert result is not source


def test_reject_non_string_sequence_member() -> None:
    with pytest.raises(
        TypeError,
        match="plugin inject must be a string sequence or mapping",
    ):
        normalize_inject(["database", 42])


def test_reject_non_string_mapping_key() -> None:
    with pytest.raises(
        TypeError,
        match="plugin inject mapping keys must be strings",
    ):
        normalize_inject({42: None})


def test_inject_decorator_attaches_dependencies() -> None:
    @inject("database", cache={"required": False})
    def sample_plugin() -> None:
        pass

    assert sample_plugin.inject == {
        "database": None,
        "cache": {"required": False},
    }


def test_plugin_spec_is_immutable() -> None:
    def sample_plugin() -> None:
        pass

    spec = PluginSpec(
        callback=sample_plugin,
        name="sample",
        inject={"database": None},
    )

    with pytest.raises(AttributeError):
        spec.name = "changed"