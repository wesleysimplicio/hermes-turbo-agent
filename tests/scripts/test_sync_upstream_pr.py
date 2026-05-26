"""Tests for scripts/sync_upstream_pr.py (auto-sync-pr workflow)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sync_upstream_pr as s  # noqa: E402


class _R:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _git_factory(responses):
    """Build a GitRunner that maps a tuple-key of args to a canned result."""
    calls = []

    def git(args):
        calls.append(list(args))
        key = tuple(args)
        # match by exact, then by first token
        if key in responses:
            return responses[key]
        for k, v in responses.items():
            if k and args[: len(k)] == list(k):
                return v
        return _R()

    git.calls = calls
    return git


def test_nothing_to_merge():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(),
        ("rev-list",): _R(stdout="0\n"),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (True, "ok"))
    assert res.ok
    assert res.nothing_to_merge
    assert res.exit_code() == s.EXIT_NOTHING


def test_fetch_failure_is_error():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(returncode=1, stderr="could not resolve host"),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (True, "ok"))
    assert not res.ok
    assert "fetch upstream failed" in res.error
    assert res.exit_code() == s.EXIT_ERROR


def test_clean_merge_and_gate_pass_is_ready():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(),
        ("rev-list",): _R(stdout="5\n"),
        ("checkout",): _R(),
        ("merge", "--no-edit"): _R(),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (True, "green"),
                 now="20260101-000000")
    assert res.ok
    assert res.merged
    assert res.gate_passed
    assert res.branch == "sync/upstream-20260101-000000"
    assert res.exit_code() == s.EXIT_READY


def test_merge_conflicts_reported_and_aborted():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(),
        ("rev-list",): _R(stdout="3\n"),
        ("checkout",): _R(),
        ("merge", "--no-edit"): _R(returncode=1, stderr="CONFLICT"),
        ("diff", "--name-only", "--diff-filter=U"): _R(stdout="a.py\nb.py\n"),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (True, "ok"))
    assert res.conflicts == ["a.py", "b.py"]
    assert not res.gate_passed
    assert res.exit_code() == s.EXIT_CONFLICTS
    # merge --abort must have been issued
    assert ["merge", "--abort"] in git.calls


def test_gate_failure_is_reported():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(),
        ("rev-list",): _R(stdout="2\n"),
        ("checkout",): _R(),
        ("merge", "--no-edit"): _R(),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (False, "pytest gate failed: boom"))
    assert res.merged
    assert not res.gate_passed
    assert "boom" in res.error
    assert res.exit_code() == s.EXIT_GATE_FAILED


def test_branch_creation_failure():
    git = _git_factory({
        ("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="codex/main\n"),
        ("fetch",): _R(),
        ("rev-list",): _R(stdout="1\n"),
        ("checkout",): _R(returncode=1, stderr="cannot create"),
    })
    res = s.sync(Path("/x"), git=git, gate=lambda: (True, "ok"))
    assert not res.ok
    assert "could not create branch" in res.error


def test_detect_base_branch():
    git = _git_factory({("rev-parse", "--abbrev-ref", "HEAD"): _R(stdout="my-branch\n")})
    assert s.detect_base_branch(git) == "my-branch"


def test_run_gate_policy_failure_short_circuits():
    def runner(cmd):
        if "validate_sync_policy.py" in " ".join(cmd):
            return _R(returncode=1, stdout='{"ok": false}')
        return _R()
    passed, detail = s.run_gate(Path("/x"), runner=runner)
    assert not passed
    assert "sync-policy validator failed" in detail


def test_run_gate_skip_tests_passes_on_policy_only():
    def runner(cmd):
        return _R(returncode=0)
    passed, detail = s.run_gate(Path("/x"), runner=runner, skip_tests=True)
    assert passed
    assert "tests skipped" in detail


def test_run_gate_full_pass():
    def runner(cmd):
        return _R(returncode=0)
    passed, detail = s.run_gate(Path("/x"), runner=runner)
    assert passed
    assert "focused tests passed" in detail


def test_exit_code_mapping():
    assert s.SyncResult(ok=False).exit_code() == s.EXIT_ERROR
    assert s.SyncResult(ok=True, nothing_to_merge=True).exit_code() == s.EXIT_NOTHING
    assert s.SyncResult(ok=True, conflicts=["x"]).exit_code() == s.EXIT_CONFLICTS
    assert s.SyncResult(ok=True, merged=True, gate_passed=False).exit_code() == s.EXIT_GATE_FAILED
    assert s.SyncResult(ok=True, merged=True, gate_passed=True).exit_code() == s.EXIT_READY
