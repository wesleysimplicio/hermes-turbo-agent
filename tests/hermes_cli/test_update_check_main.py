"""Tests for hermes_cli.update_check (hermes update --check-main)."""

from __future__ import annotations

from pathlib import Path

from hermes_cli import update_check
from hermes_cli.update_check import MainUpdateStatus


def _git_repo(tmp_path: Path) -> Path:
    (tmp_path / ".git").mkdir()
    return tmp_path


class _R:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def test_not_a_git_repo(tmp_path: Path):
    status = update_check.check_main(tmp_path)
    assert status.ok is False
    assert "not a git repository" in status.error


def test_up_to_date(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args == ["rev-parse", "HEAD"]:
            return _R(stdout="abc123abc123abc\n")
        if args == ["rev-parse", "FETCH_HEAD"]:
            return _R(stdout="abc123abc123abc\n")
        if args == ["rev-list", "--count", "HEAD..FETCH_HEAD"]:
            return _R(stdout="0\n")
        if args == ["rev-list", "--count", "FETCH_HEAD..HEAD"]:
            return _R(stdout="0\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    status = update_check.check_main(repo, branch="main")
    assert status.ok
    assert status.up_to_date
    assert status.behind == 0
    assert "Already up to date" in update_check.format_status(status)


def test_behind_clean_fast_forward(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args == ["rev-parse", "HEAD"]:
            return _R(stdout="local111\n")
        if args == ["rev-parse", "FETCH_HEAD"]:
            return _R(stdout="remote222\n")
        if args == ["rev-list", "--count", "HEAD..FETCH_HEAD"]:
            return _R(stdout="3\n")
        if args == ["rev-list", "--count", "FETCH_HEAD..HEAD"]:
            return _R(stdout="0\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    status = update_check.check_main(repo, branch="main")
    assert status.ok
    assert status.behind == 3
    assert status.ahead == 0
    assert status.can_fast_forward
    assert not status.applied
    assert "3 commits behind" in update_check.format_status(status)


def test_apply_performs_fast_forward(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)
    seen = []

    def fake_git(args, cwd):
        seen.append(args)
        if args == ["rev-parse", "HEAD"]:
            return _R(stdout="local111\n")
        if args == ["rev-parse", "FETCH_HEAD"]:
            return _R(stdout="remote222\n")
        if args == ["rev-list", "--count", "HEAD..FETCH_HEAD"]:
            return _R(stdout="2\n")
        if args == ["rev-list", "--count", "FETCH_HEAD..HEAD"]:
            return _R(stdout="0\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    status = update_check.check_main(repo, branch="main", apply=True)
    assert status.applied
    assert ["merge", "--ff-only", "FETCH_HEAD"] in seen
    assert "Fast-forwarded" in update_check.format_status(status)


def test_diverged_refuses_fast_forward(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args == ["rev-parse", "HEAD"]:
            return _R(stdout="local111\n")
        if args == ["rev-parse", "FETCH_HEAD"]:
            return _R(stdout="remote222\n")
        if args == ["rev-list", "--count", "HEAD..FETCH_HEAD"]:
            return _R(stdout="2\n")
        if args == ["rev-list", "--count", "FETCH_HEAD..HEAD"]:
            return _R(stdout="1\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    status = update_check.check_main(repo, branch="main", apply=True)
    assert status.behind == 2
    assert status.ahead == 1
    assert not status.can_fast_forward
    assert not status.applied
    assert "ahead" in update_check.format_status(status)


def test_fetch_network_error(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args[:1] == ["fetch"]:
            return _R(returncode=1,
                      stderr="fatal: unable to access 'https://...': Could not resolve host: github.com")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    status = update_check.check_main(repo, branch="main")
    assert not status.ok
    assert "network error" in status.error


def test_detect_default_branch_from_symbolic_ref(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args == ["symbolic-ref", "refs/remotes/origin/HEAD"]:
            return _R(stdout="refs/remotes/origin/codex/hermes-agent-100x-fast\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    assert update_check.detect_default_branch(repo) == "codex/hermes-agent-100x-fast"


def test_detect_default_branch_from_remote_show(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    def fake_git(args, cwd):
        if args == ["symbolic-ref", "refs/remotes/origin/HEAD"]:
            return _R(returncode=1)
        if args == ["remote", "show", "origin"]:
            return _R(stdout="* remote origin\n  HEAD branch: main\n")
        return _R()

    monkeypatch.setattr(update_check, "_run_git", fake_git)
    assert update_check.detect_default_branch(repo) == "main"


def test_run_check_main_exit_codes(monkeypatch, tmp_path: Path):
    repo = _git_repo(tmp_path)

    monkeypatch.setattr(update_check, "check_main",
                        lambda *a, **k: MainUpdateStatus(ok=True, branch="main", behind=0))
    assert update_check.run_check_main(repo) == 0

    monkeypatch.setattr(update_check, "check_main",
                        lambda *a, **k: MainUpdateStatus(ok=True, branch="main", behind=4, ahead=0))
    assert update_check.run_check_main(repo) == 2

    monkeypatch.setattr(update_check, "check_main",
                        lambda *a, **k: MainUpdateStatus(ok=False, error="boom"))
    assert update_check.run_check_main(repo) == 1

    monkeypatch.setattr(update_check, "check_main",
                        lambda *a, **k: MainUpdateStatus(ok=True, branch="main", behind=2, applied=True))
    assert update_check.run_check_main(repo, apply=True) == 0


def test_status_to_dict_has_derived_fields():
    s = MainUpdateStatus(ok=True, branch="main", behind=2, ahead=0)
    d = s.to_dict()
    assert d["up_to_date"] is False
    assert d["can_fast_forward"] is True
