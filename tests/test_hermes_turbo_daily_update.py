"""Unit tests for scripts/hermes_turbo_daily_update.py.

The daily update script is the most critical piece of upstream sync automation.
These tests cover the pieces that run in-process — retry logic, conflict
handling, personality assertion, and report writing — by mocking git/network
operations rather than touching the network.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "hermes_turbo_daily_update.py"


@pytest.fixture(scope="module")
def daily():
    spec = importlib.util.spec_from_file_location("hermes_turbo_daily_update", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hermes_turbo_daily_update"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


# ─── _looks_transient ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "stderr",
    [
        "fatal: unable to access: Could not resolve host: github.com",
        "RPC failed; curl 18 transfer closed",
        "early EOF",
        "fatal: the remote end hung up unexpectedly",
        "Operation timed out after 30005 milliseconds",
        "SSL_read: error 0x1234",
        "HTTP 503 Service Unavailable",
    ],
)
def test_looks_transient_recognizes_network_markers(daily, stderr):
    assert daily._looks_transient(stderr) is True


@pytest.mark.parametrize(
    "stderr",
    [
        "fatal: Authentication failed",
        "fatal: not a git repository",
        "error: pathspec 'foo' did not match any file(s) known to git",
        "",
    ],
)
def test_looks_transient_skips_permanent_errors(daily, stderr):
    assert daily._looks_transient(stderr) is False


# ─── _retry_network ────────────────────────────────────────────────────────────


def test_retry_network_returns_first_success(daily):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _completed(0, stdout="ok")

    with patch.object(daily, "_run", side_effect=fake_run), patch.object(
        daily.time, "sleep"
    ) as sleep_mock:
        result = daily._retry_network(["git", "fetch", "origin"], cwd=Path("/tmp"))
    assert result.returncode == 0
    assert len(calls) == 1
    assert sleep_mock.call_count == 0


def test_retry_network_retries_transient_then_succeeds(daily):
    outcomes = iter(
        [
            _completed(128, stderr="Could not resolve host: github.com"),
            _completed(128, stderr="RPC failed"),
            _completed(0, stdout="ok"),
        ]
    )

    with patch.object(daily, "_run", side_effect=lambda *a, **kw: next(outcomes)), patch.object(
        daily.time, "sleep"
    ) as sleep_mock:
        result = daily._retry_network(["git", "fetch", "origin"], cwd=Path("/tmp"))
    assert result.returncode == 0
    assert sleep_mock.call_count == 2  # two transient failures = two sleeps


def test_retry_network_aborts_on_permanent_error(daily):
    with patch.object(
        daily,
        "_run",
        side_effect=lambda *a, **kw: _completed(128, stderr="fatal: Authentication failed"),
    ), patch.object(daily.time, "sleep"):
        with pytest.raises(daily.StepError, match="permanent"):
            daily._retry_network(["git", "push"], cwd=Path("/tmp"))


def test_retry_network_gives_up_after_max_attempts(daily):
    with patch.object(
        daily,
        "_run",
        side_effect=lambda *a, **kw: _completed(128, stderr="Could not resolve host"),
    ), patch.object(daily.time, "sleep"):
        with pytest.raises(daily.StepError, match="transient retries"):
            daily._retry_network(["git", "fetch"], cwd=Path("/tmp"), attempts=2)


# ─── _merge_upstream conflict handling ─────────────────────────────────────────


def test_merge_upstream_returns_silently_on_clean_merge(daily, tmp_path):
    with patch.object(daily, "_git", return_value=_completed(0)):
        daily._merge_upstream(tmp_path, "codex/hermes-turbo-daily-20260522", tmp_path / "state")


def test_merge_upstream_raises_conflict_and_snapshots_state(daily, tmp_path):
    state_dir = tmp_path / "state"
    base_branch = "codex/hermes-turbo-daily-20260522"

    call_log: list[list[str]] = []

    def fake_git(_cwd, *args, check=True):
        call_log.append(list(args))
        # First call: merge upstream/main -> conflict (exit 1)
        if args[:2] == ("merge", "--no-edit"):
            return _completed(1, stderr="CONFLICT")
        # Second call: list conflicted paths
        if args[:1] == ("diff",) and "--diff-filter=U" in args:
            return _completed(0, stdout="agent/foo.py\ntests/test_foo.py\n")
        # Subsequent staging/commit/checkout calls succeed
        return _completed(0)

    with patch.object(daily, "_git", side_effect=fake_git):
        with pytest.raises(daily.ConflictError) as exc_info:
            daily._merge_upstream(tmp_path, base_branch, state_dir)

    assert exc_info.value.wip_branch == f"{base_branch}-CONFLICT"
    assert "agent/foo.py" in exc_info.value.conflicts
    assert "tests/test_foo.py" in exc_info.value.conflicts

    report_md = (state_dir / "latest-conflicts.md").read_text(encoding="utf-8")
    assert f"{base_branch}-CONFLICT" in report_md
    assert "agent/foo.py" in report_md
    assert "tests/test_foo.py" in report_md

    # Must have attempted to stage, commit, and create the WIP branch
    assert any(args[:1] == ["add"] for args in call_log)
    assert any(args[:1] == ["commit"] for args in call_log)
    assert any(args[:3] == ["checkout", "-B", f"{base_branch}-CONFLICT"] for args in call_log)


# ─── _assert_hermes_turbo_personality ──────────────────────────────────────────


def test_assert_personality_passes_on_real_repo(daily):
    """Markers must survive in the actual repo — this catches accidental rebrand regressions."""
    daily._assert_hermes_turbo_personality(REPO_ROOT)


def test_assert_personality_raises_when_marker_missing(daily, tmp_path):
    (tmp_path / "README.md").write_text("Hermes Turbo Agent\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("msgspec\n", encoding="utf-8")
    (tmp_path / "hermes_constants.py").write_text("# no env var here\n", encoding="utf-8")
    (tmp_path / "agent").mkdir()
    (tmp_path / "agent" / "_fastjson.py").write_text("orjson\n", encoding="utf-8")

    with pytest.raises(daily.StepError, match="HERMES_TURBO_HOME"):
        daily._assert_hermes_turbo_personality(tmp_path)


# ─── _write_report ─────────────────────────────────────────────────────────────


def test_write_report_emits_json_and_markdown(daily, tmp_path):
    report = {
        "status": "passed",
        "started_at": "2026-05-22T06:30:00",
        "finished_at": "2026-05-22T06:42:11",
        "branch": "codex/hermes-turbo-daily-20260522-063000",
        "worktree": str(tmp_path / "checkout"),
        "steps": ["prepared isolated checkout", "merged upstream/main"],
        "pr_body_path": str(tmp_path / "latest_pr_body.md"),
    }
    daily._write_report(report, tmp_path)

    parsed = json.loads((tmp_path / "latest.json").read_text(encoding="utf-8"))
    assert parsed["status"] == "passed"
    assert parsed["steps"] == report["steps"]

    md = (tmp_path / "latest.md").read_text(encoding="utf-8")
    assert "Hermes Turbo Agent Daily Hermes Sync" in md
    assert "codex/hermes-turbo-daily-20260522-063000" in md
    assert "prepared isolated checkout" in md
    assert "merged upstream/main" in md


def test_write_report_includes_error_block(daily, tmp_path):
    report = {
        "status": "failed",
        "started_at": "2026-05-22T06:30:00",
        "finished_at": "2026-05-22T06:31:00",
        "branch": "codex/hermes-turbo-daily-20260522-063000",
        "worktree": str(tmp_path / "checkout"),
        "steps": ["prepared isolated checkout"],
        "error": "upstream fetch failed after 4 retries",
    }
    daily._write_report(report, tmp_path)

    md = (tmp_path / "latest.md").read_text(encoding="utf-8")
    assert "## Error" in md
    assert "upstream fetch failed" in md
