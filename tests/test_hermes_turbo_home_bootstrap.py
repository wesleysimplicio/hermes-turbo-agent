"""Tests for ``agent.tota_home_bootstrap`` (Sprint 1 / issue #27)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from agent import tota_home_bootstrap


@pytest.fixture(autouse=True)
def _reset_bootstrap_guard():
    tota_home_bootstrap.reset_for_tests()
    yield
    tota_home_bootstrap.reset_for_tests()


@pytest.fixture
def fresh_tota_home(tmp_path, monkeypatch):
    home = tmp_path / "tota-home"
    monkeypatch.setenv("TOTA_HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    return home


def test_bootstrap_seeds_all_files_into_fresh_home(fresh_tota_home):
    results = tota_home_bootstrap.bootstrap_tota_home()

    assert (fresh_tota_home / "HERMES_BASE").exists()
    assert (fresh_tota_home / "version").exists()
    assert (fresh_tota_home / "memories" / "MEMORY.md").exists()
    assert (fresh_tota_home / "mapped_projects.json").exists()

    assert results["HERMES_BASE"] == "copied"
    assert results["version"] == "copied"
    assert results["memories/MEMORY.md"] == "copied"
    assert results["mapped_projects.json"] == "copied"


def test_bootstrap_preserves_existing_files(fresh_tota_home):
    fresh_tota_home.mkdir(parents=True)
    (fresh_tota_home / "memories").mkdir()
    (fresh_tota_home / "memories" / "MEMORY.md").write_text("operator memory")

    results = tota_home_bootstrap.bootstrap_tota_home()

    assert (fresh_tota_home / "memories" / "MEMORY.md").read_text() == "operator memory"
    assert results["memories/MEMORY.md"] == "skipped-exists"
    assert results["HERMES_BASE"] == "copied"


def test_bootstrap_is_idempotent(fresh_tota_home):
    first = tota_home_bootstrap.bootstrap_tota_home()
    assert first["HERMES_BASE"] == "copied"

    tota_home_bootstrap.reset_for_tests()
    second = tota_home_bootstrap.bootstrap_tota_home()
    assert second["HERMES_BASE"] == "skipped-exists"


def test_bootstrap_force_reseed_overwrites_existing(fresh_tota_home):
    tota_home_bootstrap.bootstrap_tota_home()

    target = fresh_tota_home / "version"
    target.write_text("operator override\n")
    assert target.read_text() == "operator override\n"

    tota_home_bootstrap.reset_for_tests()
    tota_home_bootstrap.bootstrap_tota_home(force_reseed=True)

    assert target.read_text() != "operator override\n"
    # The repo's .tota/version is the source of truth — track whatever
    # the current Tota version pin says, not a hardcoded value.
    repo_version = (
        (tota_home_bootstrap._repo_root() / ".tota" / "version").read_text().strip()
    )
    assert repo_version in target.read_text()


def test_bootstrap_only_runs_once_per_process(fresh_tota_home):
    first = tota_home_bootstrap.bootstrap_tota_home()
    second = tota_home_bootstrap.bootstrap_tota_home()

    assert first  # non-empty
    assert second == {}  # guard short-circuits


def test_bootstrap_honors_hermes_home_legacy_var(tmp_path, monkeypatch):
    legacy_home = tmp_path / "legacy-home"
    monkeypatch.delenv("TOTA_HOME", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(legacy_home))

    tota_home_bootstrap.bootstrap_tota_home()

    assert (legacy_home / "HERMES_BASE").exists()


def test_bootstrap_silent_when_source_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("TOTA_HOME", str(tmp_path / "home"))
    monkeypatch.setattr(
        tota_home_bootstrap, "_source_dir", lambda: tmp_path / "nonexistent"
    )

    results = tota_home_bootstrap.bootstrap_tota_home()
    assert results == {}


def test_bootstrap_handles_unwritable_home_gracefully(tmp_path, monkeypatch):
    if os.name == "nt":
        pytest.skip("Permission semantics differ on Windows.")
    if os.geteuid() == 0:
        pytest.skip("Root bypasses POSIX file-mode permissions.")
    locked_parent = tmp_path / "locked"
    locked_parent.mkdir()
    locked_parent.chmod(0o500)
    monkeypatch.setenv("TOTA_HOME", str(locked_parent / "home"))

    results = tota_home_bootstrap.bootstrap_tota_home()
    locked_parent.chmod(0o700)

    assert any("error" in v for v in results.values())


def test_bootstrap_returns_relative_paths_as_keys(fresh_tota_home):
    results = tota_home_bootstrap.bootstrap_tota_home()

    for key in results:
        if key.startswith("_"):
            continue
        assert not Path(key).is_absolute()
