"""Tests for ``agent.telemetry.tool_replay`` (Proposta A)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.telemetry.tool_replay import (
    ToolReplayer,
    record_tool_call,
    replay_if_hit,
    replay_path,
    tool_call_key,
)


def test_key_is_deterministic_for_same_args() -> None:
    k1 = tool_call_key("search", {"q": "hello", "limit": 10})
    k2 = tool_call_key("search", {"limit": 10, "q": "hello"})
    assert k1 == k2


def test_key_differs_for_different_name() -> None:
    assert tool_call_key("search", {"q": "x"}) != tool_call_key("fetch", {"q": "x"})


def test_key_differs_for_different_args() -> None:
    assert tool_call_key("s", {"q": "a"}) != tool_call_key("s", {"q": "b"})


def test_record_creates_file(tmp_path: Path) -> None:
    rec = record_tool_call(
        name="search", args={"q": "ai"}, output={"results": ["r1", "r2"]},
        elapsed_ms=42, directory=tmp_path,
    )
    path = replay_path(rec.sha, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["name"] == "search"
    assert data["output"] == {"results": ["r1", "r2"]}
    assert data["elapsed_ms"] == 42


def test_record_is_append_only(tmp_path: Path) -> None:
    first = record_tool_call(
        name="s", args={"q": "a"}, output="first", directory=tmp_path,
    )
    second = record_tool_call(
        name="s", args={"q": "a"}, output="second-IGNORED", directory=tmp_path,
    )
    assert first.sha == second.sha
    assert second.output == "first"  # second call did not overwrite


def test_replay_miss_returns_none(tmp_path: Path) -> None:
    assert replay_if_hit("never", {"q": "x"}, tmp_path) is None


def test_replay_hit_returns_record(tmp_path: Path) -> None:
    record_tool_call(
        name="weather", args={"city": "BSB"}, output={"temp": 28},
        directory=tmp_path,
    )
    hit = replay_if_hit("weather", {"city": "BSB"}, tmp_path)
    assert hit is not None
    assert hit.output == {"temp": 28}


def test_replayer_metrics(tmp_path: Path) -> None:
    r = ToolReplayer(directory=tmp_path)
    assert r.lookup("x", {"a": 1}) is None  # miss
    r.observe("x", {"a": 1}, output="ok", elapsed_ms=100)
    assert r.lookup("x", {"a": 1}) is not None  # hit
    assert r.lookup("x", {"a": 1}) is not None  # hit again
    assert r.metrics.hits == 2
    assert r.metrics.misses == 1
    assert r.metrics.hit_rate == pytest.approx(2 / 3)
    assert r.metrics.elapsed_ms_saved == 200


def test_replayer_handles_none_args(tmp_path: Path) -> None:
    r = ToolReplayer(directory=tmp_path)
    r.observe("now", None, output={"ts": "2026-01-01"})
    rec = r.lookup("now", None)
    assert rec is not None
    assert rec.output == {"ts": "2026-01-01"}
