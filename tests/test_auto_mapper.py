"""Tests for ``agent.auto_mapper`` (Sprint 1 / issue #26)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from agent import auto_mapper


@pytest.fixture(autouse=True)
def _reset_dedup():
    auto_mapper.reset_for_tests()
    yield
    auto_mapper.reset_for_tests()


@pytest.fixture
def fake_project(tmp_path):
    project = tmp_path / "myproject"
    project.mkdir()
    (project / ".git").mkdir()
    return project


@pytest.fixture
def captured_subprocess(monkeypatch):
    captured: list[tuple] = []

    def _fake_run(cmd, **kwargs):
        captured.append((tuple(cmd), kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout='{"ok": true, "skipped": false, "entry": {}}',
            stderr="",
        )

    monkeypatch.setattr(auto_mapper.subprocess, "run", _fake_run)
    return captured


def test_skips_when_HERMES_TURBO_AUTO_MAP_disabled(monkeypatch, fake_project, captured_subprocess):
    monkeypatch.setenv("HERMES_TURBO_AUTO_MAP", "0")
    status = auto_mapper.maybe_map_project(fake_project)

    assert status["ran"] is False
    assert status["reason"] == "disabled"
    assert captured_subprocess == []


def test_skips_when_HERMES_AUTO_MAP_disabled(monkeypatch, fake_project, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_AUTO_MAP", "false")
    status = auto_mapper.maybe_map_project(fake_project)

    assert status["ran"] is False
    assert status["reason"] == "disabled"


def test_skips_when_sentinel_file_exists(monkeypatch, tmp_path, fake_project, captured_subprocess):
    home = tmp_path / "home"
    home.mkdir()
    (home / ".disable_auto_mapper").touch()
    monkeypatch.setenv("HERMES_TURBO_HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)

    status = auto_mapper.maybe_map_project(fake_project)

    assert status["ran"] is False
    assert status["reason"] == "disabled"


def test_skips_when_not_a_code_project(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))

    plain_dir = tmp_path / "scratch"
    plain_dir.mkdir()
    status = auto_mapper.maybe_map_project(plain_dir)

    assert status["ran"] is False
    assert status["reason"] == "not-code-project"


def test_skips_when_home_dir(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "hermes-turbo"))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path / "user_home"))

    user_home = tmp_path / "user_home"
    user_home.mkdir()
    (user_home / ".git").mkdir()  # even if git exists, home dir is skipped

    status = auto_mapper.maybe_map_project(user_home)
    assert status["ran"] is False
    assert status["reason"] == "home-dir"


def test_skips_own_repo(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "hermes-turbo"))

    own_repo = tmp_path / "hermes-turbo-agent"
    (own_repo / ".hermes_turbo").mkdir(parents=True)
    (own_repo / ".hermes_turbo" / "HERMES_BASE").write_text("hermes-agent\n0.14.0\n")

    status = auto_mapper.maybe_map_project(own_repo)
    assert status["ran"] is False
    assert status["reason"] == "own-repo"


def test_runs_mapper_on_pyproject_project(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "hermes-turbo"))

    project = tmp_path / "py_project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='x'")

    status = auto_mapper.maybe_map_project(project)

    assert status["ran"] is True
    assert status["reason"] == "mapped"
    assert len(captured_subprocess) == 1
    cmd = captured_subprocess[0][0]
    assert "--project-root" in cmd


def test_runs_mapper_on_package_json_project(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "hermes-turbo"))

    project = tmp_path / "js_project"
    project.mkdir()
    (project / "package.json").write_text("{}")

    status = auto_mapper.maybe_map_project(project)
    assert status["ran"] is True


def test_only_runs_once_per_session_per_project(monkeypatch, fake_project, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(fake_project.parent / "hermes-turbo"))

    first = auto_mapper.maybe_map_project(fake_project)
    second = auto_mapper.maybe_map_project(fake_project)

    assert first["ran"] is True
    assert second["ran"] is False
    assert second["reason"] == "already-mapped-this-session"
    assert len(captured_subprocess) == 1


def test_uses_cwd_when_no_arg(monkeypatch, tmp_path, captured_subprocess):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "hermes-turbo"))

    project = tmp_path / "cwd_project"
    project.mkdir()
    (project / "Cargo.toml").write_text("[package]\nname='x'")
    monkeypatch.chdir(project)

    status = auto_mapper.maybe_map_project()
    assert status["ran"] is True


def test_propagates_subprocess_error(monkeypatch, fake_project):
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(fake_project.parent / "hermes-turbo"))

    def _raise(*a, **k):
        raise OSError("simulated")

    monkeypatch.setattr(auto_mapper.subprocess, "run", _raise)

    status = auto_mapper.maybe_map_project(fake_project)
    assert status["ran"] is False
    reason = status["reason"]
    assert isinstance(reason, str)
    assert "spawn-error" in reason


def test_nonzero_exit_does_not_mark_project_done(monkeypatch, fake_project):
    """Closes Copilot review: non-zero exit must allow retry within the same process."""
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(fake_project.parent / "hermes-turbo"))

    def _fail(cmd, **kwargs):
        return SimpleNamespace(returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(auto_mapper.subprocess, "run", _fail)

    first = auto_mapper.maybe_map_project(fake_project)
    assert first["ran"] is True
    assert first["ok"] is False
    assert first["returncode"] == 2

    # A successful retry within the same process must spawn the mapper again.
    second = auto_mapper.maybe_map_project(fake_project)
    assert second["ran"] is True  # not deduped because the first failed


def test_ok_false_payload_does_not_mark_project_done(monkeypatch, fake_project):
    """Closes Copilot review: ok=false payload should not silently dedup."""
    monkeypatch.delenv("HERMES_TURBO_AUTO_MAP", raising=False)
    monkeypatch.delenv("HERMES_AUTO_MAP", raising=False)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(fake_project.parent / "hermes-turbo"))

    def _fake(cmd, **kwargs):
        return SimpleNamespace(
            returncode=0,
            stdout='{"ok": false, "error": "npx missing"}',
            stderr="",
        )

    monkeypatch.setattr(auto_mapper.subprocess, "run", _fake)

    first = auto_mapper.maybe_map_project(fake_project)
    assert first["ran"] is True
    assert first["ok"] is False
    reason = first["reason"]
    assert isinstance(reason, str) and "npx missing" in reason

    second = auto_mapper.maybe_map_project(fake_project)
    assert second["ran"] is True  # retry allowed
