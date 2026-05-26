"""Tests for scripts/check_upstream_updates.py (auto-update-check workflow)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import check_upstream_updates as cuu  # noqa: E402


def test_in_sync_returns_no_drift():
    state = {
        "upstream_url": "https://example.test/up.git",
        "upstream_branch": "main",
        "last_sync_sha": "deadbeef",
    }
    verdict = cuu.check(state, head_resolver=lambda url, br: "deadbeef")
    assert verdict["ok"] is True
    assert verdict["drift"] is False
    assert verdict["reason"] == "in sync"


def test_upstream_advanced_returns_drift():
    state = {
        "upstream_url": "https://example.test/up.git",
        "upstream_branch": "main",
        "last_sync_sha": "oldsha",
    }
    verdict = cuu.check(state, head_resolver=lambda url, br: "newsha")
    assert verdict["ok"] is True
    assert verdict["drift"] is True
    assert verdict["remote_head"] == "newsha"


def test_no_baseline_is_treated_as_drift():
    state = {
        "upstream_url": "https://example.test/up.git",
        "upstream_branch": "main",
        "last_sync_sha": "",
    }
    verdict = cuu.check(state, head_resolver=lambda url, br: "whatever")
    assert verdict["ok"] is True
    assert verdict["drift"] is True
    assert "first sync" in verdict["reason"]


def test_unreachable_remote_is_error():
    state = {"last_sync_sha": "x"}
    verdict = cuu.check(state, head_resolver=lambda url, br: None)
    assert verdict["ok"] is False
    assert "could not read upstream HEAD" in verdict["error"]


def test_defaults_when_state_empty():
    verdict = cuu.check({}, head_resolver=lambda url, br: "abc")
    assert verdict["upstream_url"].endswith("NousResearch/hermes-agent.git")
    assert verdict["upstream_branch"] == "main"
    # empty state has no baseline → drift
    assert verdict["drift"] is True


def test_load_sync_state_missing(tmp_path: Path):
    assert cuu.load_sync_state(tmp_path / "nope.json") == {}


def test_load_sync_state_malformed(tmp_path: Path):
    p = tmp_path / "bad.json"
    p.write_text("{not json")
    assert cuu.load_sync_state(p) == {}


def test_load_sync_state_valid(tmp_path: Path):
    p = tmp_path / "state.json"
    p.write_text(json.dumps({"last_sync_sha": "abc", "upstream_branch": "main"}))
    state = cuu.load_sync_state(p)
    assert state["last_sync_sha"] == "abc"


def test_main_exit_codes(tmp_path, monkeypatch, capsys):
    # drift → 10
    state_path = tmp_path / "s.json"
    state_path.write_text(json.dumps({
        "upstream_url": "https://example.test/up.git",
        "upstream_branch": "main",
        "last_sync_sha": "old",
    }))
    monkeypatch.setattr(cuu, "ls_remote_head", lambda url, br: "new")
    rc = cuu.main(["--state", str(state_path)])
    assert rc == cuu.EXIT_DRIFT
    out = json.loads(capsys.readouterr().out)
    assert out["drift"] is True

    # in sync → 0
    monkeypatch.setattr(cuu, "ls_remote_head", lambda url, br: "old")
    rc = cuu.main(["--state", str(state_path)])
    assert rc == cuu.EXIT_UP_TO_DATE

    # error → 1
    monkeypatch.setattr(cuu, "ls_remote_head", lambda url, br: None)
    rc = cuu.main(["--state", str(state_path)])
    assert rc == cuu.EXIT_ERROR
