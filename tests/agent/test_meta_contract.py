"""Tests for ``agent.meta_contract``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.meta_contract import (
    HermesMeta,
    check_write,
    list_violations,
    load_meta,
)


def _w_meta(root: Path, **overrides) -> None:
    payload = {
        "managed_paths": ["agent/**", "tests/**"],
        "read_only_globs": [".git/**", "*.lock"],
        "init_must_merge": ["CLAUDE.md"],
        "init_must_ask": ["PRD.md"],
        "policy": {
            "on_read_only_violation": "block",
            "on_init_must_merge": "warn",
            "on_init_must_ask": "ask",
        },
    }
    payload.update(overrides)
    (root / ".hermes-meta.json").write_text(json.dumps(payload), encoding="utf-8")


def test_load_meta_missing_returns_none(tmp_path: Path) -> None:
    assert load_meta(tmp_path) is None


def test_load_meta_invalid_returns_none(tmp_path: Path) -> None:
    (tmp_path / ".hermes-meta.json").write_text("{not json", encoding="utf-8")
    assert load_meta(tmp_path) is None


def test_load_meta_parses_fields(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None
    assert meta.managed_paths == ("agent/**", "tests/**")
    assert meta.read_only_globs == (".git/**", "*.lock")
    assert meta.on_read_only_violation == "block"


def test_check_write_blocks_read_only(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    target = tmp_path / "uv.lock"
    target.write_text("x", encoding="utf-8")
    decision = check_write(meta, target)
    assert decision.blocked is True
    assert decision.rule == "read_only_globs"


def test_check_write_allows_managed(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    (tmp_path / "agent").mkdir()
    target = tmp_path / "agent" / "foo.py"
    decision = check_write(meta, target)
    assert decision.blocked is False
    assert decision.action == "allow"
    assert decision.rule == "managed_paths"


def test_check_write_init_must_ask(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    target = tmp_path / "PRD.md"
    decision = check_write(meta, target)
    assert decision.action == "ask"
    assert decision.rule == "init_must_ask"


def test_check_write_init_must_merge_warns(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    target = tmp_path / "CLAUDE.md"
    decision = check_write(meta, target)
    assert decision.blocked is False
    assert decision.action == "warn"
    assert decision.rule == "init_must_merge"


def test_out_of_scope_warns_not_blocks(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    (tmp_path / "random").mkdir()
    target = tmp_path / "random" / "x.txt"
    decision = check_write(meta, target)
    assert decision.blocked is False
    assert decision.action == "warn"
    assert decision.rule == "out_of_scope"


def test_list_violations_filters(tmp_path: Path) -> None:
    _w_meta(tmp_path)
    meta = load_meta(tmp_path)
    assert meta is not None

    (tmp_path / "agent").mkdir()
    safe = tmp_path / "agent" / "ok.py"
    lock = tmp_path / "uv.lock"

    blocked = list_violations(meta, [safe, lock])
    assert len(blocked) == 1
    assert blocked[0].rule == "read_only_globs"
