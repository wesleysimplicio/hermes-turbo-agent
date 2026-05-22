"""Tests for ``TupleStatusEnvelope`` (P4)."""

from __future__ import annotations

import pytest

from agent.contracts import TupleStatusEnvelope


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in (
        "HERMES_RUNTIME_STATUS",
        "HERMES_RUNTIME_STATUS_SNAPSHOT",
        "HERMES_RUNTIME_STATUS_ACTIVE",
        "HERMES_RUNTIME_STATUS_TOTAL",
        "HERMES_RUNTIME_STATUS_NEXT",
        "HERMES_RUNTIME_STATUS_PARTIAL",
    ):
        monkeypatch.delenv(key, raising=False)


def test_default_is_silent() -> None:
    env = TupleStatusEnvelope(snapshot="x", active="1", total="1",
                              next_yool="y", partial="p")
    assert env.render() is None


def test_master_switch_enables_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_RUNTIME_STATUS", "true")
    env = TupleStatusEnvelope(
        snapshot="snap", active="2", total="5",
        next_yool="agent.dev.python", partial="ok",
    )
    out = env.render()
    assert out is not None
    assert "[Tuple Space Snapshot] snap" in out
    assert "[Active Agents/Subagents] 2" in out
    assert "[Total Agents/Subagents] 5" in out
    assert "[Próximo Yool a executar] agent.dev.python" in out
    assert "[Resultado parcial] ok" in out


def test_per_field_toggle(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_RUNTIME_STATUS_SNAPSHOT", "true")
    env = TupleStatusEnvelope(snapshot="only-this", active="x", total="x",
                              next_yool="x", partial="x")
    out = env.render()
    assert out is not None
    assert "[Tuple Space Snapshot] only-this" in out
    assert "[Active" not in out
    assert "[Resultado parcial" not in out


def test_per_field_overrides_master(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HERMES_RUNTIME_STATUS", "true")
    monkeypatch.setenv("HERMES_RUNTIME_STATUS_SNAPSHOT", "false")
    env = TupleStatusEnvelope(snapshot="hidden", active="a", total="t",
                              next_yool="n", partial="p")
    out = env.render()
    assert out is not None
    assert "[Tuple Space Snapshot]" not in out
    assert "[Active Agents/Subagents] a" in out


def test_field_truncated_to_budget() -> None:
    long = "x" * (TupleStatusEnvelope.MAX_FIELD_CHARS + 50)
    env = TupleStatusEnvelope(snapshot=long, active="", total="",
                              next_yool="", partial="")
    assert len(env.snapshot) == TupleStatusEnvelope.MAX_FIELD_CHARS
    assert env.snapshot.endswith("...")


def test_is_enabled_reads_master(monkeypatch: pytest.MonkeyPatch) -> None:
    assert TupleStatusEnvelope.is_enabled() is False
    monkeypatch.setenv("HERMES_RUNTIME_STATUS", "1")
    assert TupleStatusEnvelope.is_enabled() is True
