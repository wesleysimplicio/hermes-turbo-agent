"""Tests for the llm-project-mapper skill (Sprint 1 / issue #28).

Covers:
- ``_extract_mapper_version`` regex parsing.
- ``_ralph_ready`` artifact-set heuristic.
- ``_is_fresh`` TTL boundaries.
- ``_tota_home`` resolution order with and without ``hermes_constants``.
- ``map_project`` end-to-end with subprocess mocked.
- ``_run_mapper`` failure modes (missing npx, timeout, non-zero exit).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest


SKILL_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "software-development"
    / "llm-project-mapper"
    / "scripts"
    / "map_project.py"
)


@pytest.fixture
def mapper_module():
    """Load the skill's map_project.py as a module under the alias ``mp``."""
    spec = importlib.util.spec_from_file_location("tota_map_project", SKILL_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["tota_map_project"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    home = tmp_path / "tota-home"
    monkeypatch.setenv("TOTA_HOME", str(home))
    monkeypatch.delenv("HERMES_HOME", raising=False)
    return home


# ─────────────────────────────────────────────────────────────────────────────
# _extract_mapper_version
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_version_from_banner(mapper_module):
    stdout = "LLM Project Mapper - Bootstrap (npx)\n  v0.2.0\n========"
    assert mapper_module._extract_mapper_version(stdout) == "0.2.0"


def test_extract_version_with_prerelease(mapper_module):
    stdout = "  v1.4.2-rc.1\n"
    assert mapper_module._extract_mapper_version(stdout) == "1.4.2-rc.1"


def test_extract_version_with_build_metadata(mapper_module):
    stdout = "  v2.0.0+gabcd\n"
    assert mapper_module._extract_mapper_version(stdout) == "2.0.0+gabcd"


def test_extract_version_returns_unknown_on_empty(mapper_module):
    assert mapper_module._extract_mapper_version("") == "unknown"


def test_extract_version_returns_unknown_when_no_match(mapper_module):
    assert mapper_module._extract_mapper_version("no version here") == "unknown"


# ─────────────────────────────────────────────────────────────────────────────
# _ralph_ready
# ─────────────────────────────────────────────────────────────────────────────


def test_ralph_ready_requires_all_three_docs(tmp_path, mapper_module):
    (tmp_path / "AGENTS.md").write_text("a")
    (tmp_path / "INIT.md").write_text("i")
    (tmp_path / "_BOOTSTRAP.md").write_text("b")
    assert mapper_module._ralph_ready(tmp_path) is True


def test_ralph_ready_false_when_missing_one_doc(tmp_path, mapper_module):
    (tmp_path / "AGENTS.md").write_text("a")
    (tmp_path / "INIT.md").write_text("i")
    # _BOOTSTRAP.md intentionally missing
    assert mapper_module._ralph_ready(tmp_path) is False


def test_ralph_ready_false_on_empty_dir(tmp_path, mapper_module):
    assert mapper_module._ralph_ready(tmp_path) is False


# ─────────────────────────────────────────────────────────────────────────────
# _is_fresh
# ─────────────────────────────────────────────────────────────────────────────


def test_is_fresh_within_ttl(mapper_module):
    now = datetime.now(timezone.utc)
    entry = {"mapped_at": (now - timedelta(days=5)).isoformat().replace("+00:00", "Z")}
    assert mapper_module._is_fresh(entry, ttl_days=30) is True


def test_is_fresh_past_ttl(mapper_module):
    now = datetime.now(timezone.utc)
    entry = {"mapped_at": (now - timedelta(days=60)).isoformat().replace("+00:00", "Z")}
    assert mapper_module._is_fresh(entry, ttl_days=30) is False


def test_is_fresh_handles_missing_timestamp(mapper_module):
    assert mapper_module._is_fresh({}, ttl_days=30) is False


def test_is_fresh_handles_malformed_timestamp(mapper_module):
    assert mapper_module._is_fresh({"mapped_at": "not-a-date"}, ttl_days=30) is False


# ─────────────────────────────────────────────────────────────────────────────
# _tota_home
# ─────────────────────────────────────────────────────────────────────────────


def test_tota_home_prefers_TOTA_HOME(tmp_path, monkeypatch, mapper_module):
    monkeypatch.setenv("TOTA_HOME", str(tmp_path / "tota"))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "legacy"))
    # Force fallback by simulating import failure if needed
    result = mapper_module._tota_home()
    assert result == tmp_path / "tota"


def test_tota_home_falls_back_to_HERMES_HOME(tmp_path, monkeypatch, mapper_module):
    monkeypatch.delenv("TOTA_HOME", raising=False)
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "legacy"))
    result = mapper_module._tota_home()
    assert result == tmp_path / "legacy"


def test_tota_home_default_when_neither_set(tmp_path, monkeypatch, mapper_module):
    monkeypatch.delenv("TOTA_HOME", raising=False)
    monkeypatch.delenv("HERMES_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    result = mapper_module._tota_home()
    # Either ~/.hermes_turbo (from hermes_constants) or the fallback ~/.hermes_turbo — both valid.
    assert result.name == ".hermes_turbo"


# ─────────────────────────────────────────────────────────────────────────────
# _run_mapper failure modes
# ─────────────────────────────────────────────────────────────────────────────


def test_run_mapper_reports_missing_npx(monkeypatch, mapper_module, tmp_path):
    monkeypatch.setattr(mapper_module.shutil, "which", lambda _: None)
    ok, msg = mapper_module._run_mapper(tmp_path)
    assert ok is False
    assert "npx" in msg.lower()


def test_run_mapper_reports_timeout(monkeypatch, mapper_module, tmp_path):
    monkeypatch.setattr(mapper_module.shutil, "which", lambda _: "/usr/bin/npx")

    def _raise(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=600)

    monkeypatch.setattr(mapper_module.subprocess, "run", _raise)
    ok, msg = mapper_module._run_mapper(tmp_path)
    assert ok is False
    assert "timed out" in msg.lower()


def test_run_mapper_reports_nonzero_exit(monkeypatch, mapper_module, tmp_path):
    monkeypatch.setattr(mapper_module.shutil, "which", lambda _: "/usr/bin/npx")

    def _fake_run(*args, **kwargs):
        return SimpleNamespace(returncode=2, stdout="", stderr="boom")

    monkeypatch.setattr(mapper_module.subprocess, "run", _fake_run)
    ok, msg = mapper_module._run_mapper(tmp_path)
    assert ok is False
    assert "boom" in msg


# ─────────────────────────────────────────────────────────────────────────────
# map_project end-to-end with subprocess mocked
# ─────────────────────────────────────────────────────────────────────────────


def test_map_project_fresh_run_records_fingerprint(
    isolated_home, tmp_path, monkeypatch, mapper_module
):
    project = tmp_path / "project"
    project.mkdir()

    def _fake_run_mapper(project_root):
        (project_root / "AGENTS.md").write_text("agents")
        (project_root / "INIT.md").write_text("init")
        (project_root / "_BOOTSTRAP.md").write_text("boot")
        return True, "LLM Project Mapper\n  v0.3.1\n"

    monkeypatch.setattr(mapper_module, "_run_mapper", _fake_run_mapper)

    result = mapper_module.map_project(project, force=False, ttl_days=30)

    assert result["ok"] is True
    assert result["skipped"] is False
    assert result["entry"]["mapper_version"] == "0.3.1"
    assert result["entry"]["ralph_ready"] is True

    memory_path = isolated_home / "mapped_projects.json"
    assert memory_path.exists()
    saved = json.loads(memory_path.read_text())
    assert str(project.resolve()) in saved


def test_map_project_is_idempotent_within_ttl(
    isolated_home, tmp_path, monkeypatch, mapper_module
):
    project = tmp_path / "project"
    project.mkdir()

    invocations = []

    def _fake_run_mapper(project_root):
        invocations.append(project_root)
        (project_root / "AGENTS.md").write_text("agents")
        (project_root / "INIT.md").write_text("init")
        (project_root / "_BOOTSTRAP.md").write_text("boot")
        return True, "  v0.1.0\n"

    monkeypatch.setattr(mapper_module, "_run_mapper", _fake_run_mapper)

    first = mapper_module.map_project(project, force=False, ttl_days=30)
    second = mapper_module.map_project(project, force=False, ttl_days=30)

    assert first["skipped"] is False
    assert second["skipped"] is True
    assert second["reason"] == "already_mapped_recent"
    assert len(invocations) == 1


def test_map_project_force_reruns_even_when_fresh(
    isolated_home, tmp_path, monkeypatch, mapper_module
):
    project = tmp_path / "project"
    project.mkdir()
    invocations = []

    def _fake_run_mapper(project_root):
        invocations.append(project_root)
        (project_root / "AGENTS.md").write_text("agents")
        (project_root / "INIT.md").write_text("init")
        (project_root / "_BOOTSTRAP.md").write_text("boot")
        return True, "  v0.1.0\n"

    monkeypatch.setattr(mapper_module, "_run_mapper", _fake_run_mapper)

    mapper_module.map_project(project, force=False, ttl_days=30)
    second = mapper_module.map_project(project, force=True, ttl_days=30)

    assert second["skipped"] is False
    assert len(invocations) == 2


def test_map_project_rejects_nonexistent_root(isolated_home, tmp_path, mapper_module):
    result = mapper_module.map_project(tmp_path / "missing", force=False, ttl_days=30)
    assert result["ok"] is False
    assert "not a directory" in result["error"]


def test_map_project_propagates_mapper_failure(
    isolated_home, tmp_path, monkeypatch, mapper_module
):
    project = tmp_path / "project"
    project.mkdir()
    monkeypatch.setattr(
        mapper_module, "_run_mapper", lambda _: (False, "mapper crashed")
    )

    result = mapper_module.map_project(project, force=False, ttl_days=30)
    assert result["ok"] is False
    assert "mapper crashed" in result["error"]
