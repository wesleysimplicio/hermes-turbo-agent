"""Tests for ``agent.hermes_turbo_home_bootstrap`` (Sprint 1 / issue #27)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent import hermes_turbo_home_bootstrap


@pytest.fixture(autouse=True)
def _reset_bootstrap_guard():
    hermes_turbo_home_bootstrap.reset_for_tests()
    yield
    hermes_turbo_home_bootstrap.reset_for_tests()


@pytest.fixture
def fresh_hermes_turbo_home(tmp_path, monkeypatch):
    home = tmp_path / "hermes-turbo-home"
    monkeypatch.setenv("HERMES_TURBO_HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    return home


def test_bootstrap_seeds_all_files_into_fresh_home(fresh_hermes_turbo_home):
    results = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    assert (fresh_hermes_turbo_home / "HERMES_BASE").exists()
    assert (fresh_hermes_turbo_home / "version").exists()
    assert (fresh_hermes_turbo_home / "memories" / "MEMORY.md").exists()
    assert (fresh_hermes_turbo_home / "mapped_projects.json").exists()

    assert results["HERMES_BASE"] == "copied"
    assert results["version"] == "copied"
    assert results["memories/MEMORY.md"] == "copied"
    assert results["mapped_projects.json"] == "copied"


def test_bootstrap_preserves_existing_files(fresh_hermes_turbo_home):
    fresh_hermes_turbo_home.mkdir(parents=True)
    (fresh_hermes_turbo_home / "memories").mkdir()
    (fresh_hermes_turbo_home / "memories" / "MEMORY.md").write_text("operator memory")

    results = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    assert (fresh_hermes_turbo_home / "memories" / "MEMORY.md").read_text() == "operator memory"
    assert results["memories/MEMORY.md"] == "skipped-exists"
    assert results["HERMES_BASE"] == "copied"


def test_bootstrap_is_idempotent(fresh_hermes_turbo_home):
    first = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()
    assert first["HERMES_BASE"] == "copied"

    hermes_turbo_home_bootstrap.reset_for_tests()
    second = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()
    assert second["HERMES_BASE"] == "skipped-exists"


def test_bootstrap_force_reseed_overwrites_existing(fresh_hermes_turbo_home):
    hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    target = fresh_hermes_turbo_home / "version"
    target.write_text("operator override\n")
    assert target.read_text() == "operator override\n"

    hermes_turbo_home_bootstrap.reset_for_tests()
    hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home(force_reseed=True)

    assert target.read_text() != "operator override\n"
    # The repo's .hermes-turbo/version is the source of truth — track whatever
    # the current Hermes Turbo version pin says, not a hardcoded value.
    repo_version = (
        (hermes_turbo_home_bootstrap._repo_root() / ".hermes-turbo" / "version").read_text().strip()
    )
    assert repo_version in target.read_text()


def test_bootstrap_only_runs_once_per_process(fresh_hermes_turbo_home):
    first = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()
    second = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    assert first  # non-empty
    assert second == {}  # guard short-circuits


def test_bootstrap_honors_hermes_home_legacy_var(tmp_path, monkeypatch):
    legacy_home = tmp_path / "legacy-home"
    monkeypatch.delenv("HERMES_TURBO_HOME", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(legacy_home))

    hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    assert (legacy_home / "HERMES_BASE").exists()


def test_bootstrap_silent_when_source_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_TURBO_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        hermes_turbo_home_bootstrap, "_source_dir", lambda: tmp_path / "nonexistent"
    )

    results = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()
    assert results == {}


def test_bootstrap_handles_unwritable_home_gracefully(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip("Permission semantics differ on Windows.")
    if os.geteuid() == 0:
        pytest.skip("Root bypasses POSIX file-mode permissions.")
    locked_parent = tmp_path / "locked"
    locked_parent.mkdir()
    locked_parent.chmod(0o500)
    monkeypatch.setenv("HERMES_TURBO_HOME", str(locked_parent / "home"))

    results = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()
    locked_parent.chmod(0o700)

    assert any("error" in v for v in results.values())


def test_bootstrap_returns_relative_paths_as_keys(fresh_hermes_turbo_home):
    results = hermes_turbo_home_bootstrap.bootstrap_hermes_turbo_home()

    for key in results:
        if key.startswith("_"):
            continue
        assert not Path(key).is_absolute()
