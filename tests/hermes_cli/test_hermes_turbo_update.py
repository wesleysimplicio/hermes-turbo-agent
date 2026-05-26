"""Hermes Turbo update behavior for fork installs."""

from __future__ import annotations

from types import SimpleNamespace

from hermes_cli import main as hermes_main


def test_fork_upstream_sync_merges_official_hermes_without_push(monkeypatch, tmp_path):
    """Fork updates merge upstream/main while preserving fork-only commits."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "remote", "get-url", "upstream"]:
            return SimpleNamespace(returncode=128, stdout="", stderr="missing")
        if cmd == [
            "git",
            "remote",
            "add",
            "upstream",
            "https://github.com/NousResearch/hermes-agent.git",
        ]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "fetch", "upstream", "main", "--quiet"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-list", "--count", "upstream/main..HEAD"]:
            return SimpleNamespace(returncode=0, stdout="12\n", stderr="")
        if cmd == ["git", "rev-list", "--count", "HEAD..upstream/main"]:
            return SimpleNamespace(returncode=0, stdout="5\n", stderr="")
        if cmd == ["git", "merge", "--no-edit", "-X", "ours", "upstream/main"]:
            return SimpleNamespace(returncode=0, stdout="merged\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hermes_main.subprocess, "run", fake_run)

    assert hermes_main._sync_with_upstream_if_needed(
        ["git"], tmp_path, target_branch="codex/hermes-agent-100x-fast"
    )

    assert ["git", "merge", "--no-edit", "-X", "ours", "upstream/main"] in calls
    assert not any("push" in cmd for cmd in calls)


def test_fork_upstream_sync_keeps_fork_files_when_merge_conflicts(
    monkeypatch, tmp_path
):
    """Remaining upstream conflicts are resolved in favor of the fork."""
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "remote", "get-url", "upstream"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "fetch", "upstream", "main", "--quiet"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-list", "--count", "upstream/main..HEAD"]:
            return SimpleNamespace(returncode=0, stdout="12\n", stderr="")
        if cmd == ["git", "rev-list", "--count", "HEAD..upstream/main"]:
            return SimpleNamespace(returncode=0, stdout="5\n", stderr="")
        if cmd == ["git", "merge", "--no-edit", "-X", "ours", "upstream/main"]:
            return SimpleNamespace(returncode=1, stdout="", stderr="conflict\n")
        if cmd == ["git", "diff", "--name-only", "--diff-filter=U"]:
            return SimpleNamespace(
                returncode=0,
                stdout="tests/hermes_cli/test_update_gateway_restart.py\n",
                stderr="",
            )
        if cmd == [
            "git",
            "checkout",
            "--ours",
            "--",
            "tests/hermes_cli/test_update_gateway_restart.py",
        ]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == [
            "git",
            "add",
            "--",
            "tests/hermes_cli/test_update_gateway_restart.py",
        ]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "commit", "--no-edit"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(hermes_main.subprocess, "run", fake_run)

    assert hermes_main._sync_with_upstream_if_needed(
        ["git"], tmp_path, target_branch="codex/hermes-agent-100x-fast"
    )

    assert ["git", "commit", "--no-edit"] in calls
    assert ["git", "merge", "--abort"] not in calls
    assert not any("push" in cmd for cmd in calls)


def test_update_check_reports_fork_origin_and_upstream_separately(
    monkeypatch, tmp_path, capsys
):
    """`hermes update --check` should not collapse fork drift into origin/main."""
    project_root = tmp_path / "hermes-agent"
    project_root.mkdir()
    (project_root / ".git").mkdir()
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        if cmd == ["git", "fetch", "origin"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "remote", "get-url", "origin"]:
            return SimpleNamespace(
                returncode=0,
                stdout="https://github.com/wesleysimplicio/hermes-turbo-agent.git\n",
                stderr="",
            )
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return SimpleNamespace(
                returncode=0,
                stdout="codex/hermes-agent-100x-fast\n",
                stderr="",
            )
        if cmd == [
            "git",
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{u}",
        ]:
            return SimpleNamespace(
                returncode=0,
                stdout="origin/codex/hermes-agent-100x-fast\n",
                stderr="",
            )
        if cmd == [
            "git",
            "rev-list",
            "--count",
            "HEAD..origin/codex/hermes-agent-100x-fast",
        ]:
            return SimpleNamespace(returncode=0, stdout="0\n", stderr="")
        if cmd == ["git", "remote", "get-url", "upstream"]:
            return SimpleNamespace(
                returncode=0,
                stdout="https://github.com/NousResearch/hermes-agent.git\n",
                stderr="",
            )
        if cmd == ["git", "fetch", "upstream", "main", "--quiet"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-list", "--count", "HEAD..upstream/main"]:
            return SimpleNamespace(returncode=0, stdout="5\n", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(hermes_main.subprocess, "run", fake_run)
    monkeypatch.setattr(
        "hermes_cli.config.detect_install_method", lambda _root: "git"
    )
    monkeypatch.setattr(
        "hermes_cli.config.recommended_update_command", lambda: "hermes2 update"
    )

    hermes_main._cmd_update_check()

    out = capsys.readouterr().out
    assert "origin/codex/hermes-agent-100x-fast" in out
    assert "Official Hermes update available: 5 commits behind upstream/main" in out
    assert "origin/main" not in out
    assert not any(cmd[:3] == ["git", "rev-list", "HEAD..origin/main"] for cmd in calls)


def test_update_check_keeps_official_install_wording(monkeypatch, tmp_path, capsys):
    """Official Hermes installs should not be labeled as fork updates."""
    project_root = tmp_path / "hermes-agent"
    project_root.mkdir()
    (project_root / ".git").mkdir()

    def fake_run(cmd, **kwargs):
        if cmd == ["git", "fetch", "origin"]:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        if cmd == ["git", "rev-parse", "--abbrev-ref", "HEAD"]:
            return SimpleNamespace(returncode=0, stdout="main\n", stderr="")
        if cmd == ["git", "remote", "get-url", "origin"]:
            return SimpleNamespace(
                returncode=0,
                stdout="https://github.com/NousResearch/hermes-agent.git\n",
                stderr="",
            )
        if cmd == ["git", "rev-list", "--count", "HEAD..origin/main"]:
            return SimpleNamespace(returncode=0, stdout="2\n", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(hermes_main, "PROJECT_ROOT", project_root)
    monkeypatch.setattr(hermes_main.subprocess, "run", fake_run)
    monkeypatch.setattr(
        "hermes_cli.config.detect_install_method", lambda _root: "git"
    )
    monkeypatch.setattr(
        "hermes_cli.config.recommended_update_command", lambda: "hermes update"
    )

    hermes_main._cmd_update_check()

    out = capsys.readouterr().out
    assert "Update available: 2 commits behind origin/main" in out
    assert "Fork update available" not in out
