"""Tests for ``agent.telemetry.receipts`` (P7)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.telemetry.receipts import (
    content_hash,
    lookup_receipt,
    receipt_path,
    record_receipt,
)


def test_content_hash_is_deterministic() -> None:
    assert content_hash("abc") == content_hash("abc")
    assert content_hash("abc") != content_hash("abd")


def test_record_receipt_creates_file(tmp_path: Path) -> None:
    r = record_receipt(
        payload="rm -rf /tmp/foo",
        yool_id="agent.ops.tool_shell",
        lane="slow",
        status="ok",
        tokens=120,
        tokens_raw=300,
        tokens_saved=180,
        meta={"cwd": "/tmp"},
        directory=tmp_path,
    )
    path = receipt_path(r.sha, tmp_path)
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["sha"] == r.sha
    assert data["yool_id"] == "agent.ops.tool_shell"
    assert data["cost"]["tokens"] == 120
    assert data["cost"]["tokens_saved"] == 180
    assert data["meta"] == {"cwd": "/tmp"}


def test_record_receipt_is_append_only(tmp_path: Path) -> None:
    first = record_receipt(
        payload="x", yool_id="a.b.c", tokens=10, directory=tmp_path,
    )
    second = record_receipt(
        payload="x", yool_id="WRONG", tokens=999, directory=tmp_path,
    )
    assert first.sha == second.sha
    assert second.yool_id == "a.b.c"
    assert second.cost.tokens == 10


def test_lookup_receipt_roundtrip(tmp_path: Path) -> None:
    payload = "ls -la"
    assert lookup_receipt(payload, tmp_path) is None
    record_receipt(payload=payload, tokens=5, directory=tmp_path)
    hit = lookup_receipt(payload, tmp_path)
    assert hit is not None
    assert hit.cost.tokens == 5


def test_record_receipt_silent_on_oserror(tmp_path: Path) -> None:
    # point at a path under a read-only file to force an OSError on mkdir/write
    bad_dir = tmp_path / "file" / "not" / "a" / "dir"
    (tmp_path / "file").write_text("blocking", encoding="utf-8")
    r = record_receipt(payload="abc", directory=bad_dir)
    # returned, even when write failed
    assert r.sha == content_hash("abc")
