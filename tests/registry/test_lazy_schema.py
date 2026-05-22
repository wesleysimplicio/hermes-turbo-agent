"""Unit tests for :mod:`agent.registry.lazy_schema`."""

from __future__ import annotations

import pytest

from agent.registry.lazy_schema import LazyToolRegistry, ToolStub


def _schema_factory(calls):
    def _load():
        calls.append(1)
        return {"type": "object", "properties": {"q": {"type": "string"}}}

    return _load


def test_register_stores_only_stub():
    reg = LazyToolRegistry()
    calls = []
    reg.register("search", "Search the web.", _schema_factory(calls))
    assert reg.list() == [ToolStub("search", "Search the web.")]
    assert calls == []
    assert reg.stats() == {"registered": 1, "loaded": 0}


def test_load_schema_invokes_loader_once():
    reg = LazyToolRegistry()
    calls = []
    reg.register("search", "Search the web.", _schema_factory(calls))
    assert reg.load("search") is reg.load("search")
    assert calls == [1]
    assert reg.stats() == {"registered": 1, "loaded": 1}


def test_load_unknown_raises():
    with pytest.raises(KeyError):
        LazyToolRegistry().load("missing")


def test_register_validates_inputs():
    reg = LazyToolRegistry()
    with pytest.raises(ValueError):
        reg.register("", "x", lambda: {})
    with pytest.raises(TypeError):
        reg.register("ok", "x", "not-callable")  # type: ignore[arg-type]


def test_loader_must_return_mapping():
    reg = LazyToolRegistry()
    reg.register("bad", "broken", lambda: "not a mapping")  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError):
        reg.load("bad")


def test_register_overwrites_and_resets_cache():
    reg = LazyToolRegistry()
    reg.register("t", "v1", lambda: {"v": 1})
    assert reg.load("t") == {"v": 1}
    reg.register("t", "v2", lambda: {"v": 2})
    assert reg.load("t") == {"v": 2}
    assert reg.stats()["registered"] == 1


def test_default_registry_helpers():
    from agent.registry import lazy_schema as mod

    mod._reset_default_registry_for_tests()
    mod.register_tool("a", "alpha", lambda: {"k": "v"})
    assert [t.name for t in mod.list_tools()] == ["a"]
    assert mod.load_schema("a") == {"k": "v"}
    mod._reset_default_registry_for_tests()
