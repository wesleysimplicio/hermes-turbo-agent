"""Tests for the ``hermes skillopt`` CLI wrapper."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli import skillopt


def _write_tasks(path: Path) -> None:
    payload = {
        "train": [
            {"id": "t1", "prompt": "write a function",
             "reference": "validate inputs handle errors return value"},
            {"id": "t2", "prompt": "parse a file",
             "reference": "open parse close handle errors gracefully"},
        ],
        "val": [
            {"id": "v1", "prompt": "write a function",
             "reference": "validate inputs handle errors return value"},
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_optimize_writes_best_skill(tmp_path: Path, capsys) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n\nbare guidance\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)

    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks),
                        "--iters", "8", "--threshold", "0.95",
                        "--budget-chars", "2000"])
    assert rc == 0
    out = tmp_path / "best_skill.md"
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert len(body) > len("# Skill\n\nbare guidance\n")


def test_optimize_json_output(tmp_path: Path, capsys) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)

    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks),
                        "--iters", "5", "--threshold", "0.95", "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert "best_score" in payload
    assert "history" in payload
    assert payload["skill"] == str(skill)


def test_optimize_in_place(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)

    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks),
                        "--iters", "6", "--threshold", "0.95",
                        "--budget-chars", "2000", "--in-place"])
    assert rc == 0
    assert not (tmp_path / "best_skill.md").exists()
    assert skill.read_text(encoding="utf-8") != "# Skill\n"


def test_optimize_dry_run_writes_nothing(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)

    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks),
                        "--iters", "3", "--dry-run"])
    assert rc == 0
    assert not (tmp_path / "best_skill.md").exists()


def test_optimize_accepts_skill_directory(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)

    rc = skillopt.main(["optimize", str(tmp_path), "--tasks", str(tasks),
                        "--iters", "2"])
    assert rc == 0


def test_optimize_missing_skill_errors(tmp_path: Path) -> None:
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)
    rc = skillopt.main(["optimize", str(tmp_path / "nope.md"),
                        "--tasks", str(tasks)])
    assert rc == 1


def test_optimize_flat_task_list(tmp_path: Path) -> None:
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    tasks.write_text(json.dumps([
        {"id": "a", "prompt": "p", "reference": "alpha beta gamma"},
        {"id": "b", "prompt": "p", "reference": "delta epsilon zeta"},
    ]), encoding="utf-8")
    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks), "--iters", "3"])
    assert rc == 0


def test_no_subcommand_prints_usage(capsys) -> None:
    rc = skillopt.main([])
    assert rc == 0
    assert "Usage" in capsys.readouterr().out


def test_llm_reflector_falls_back_without_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(skillopt, "complete_via_auxiliary", lambda model: None)
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Skill\n", encoding="utf-8")
    tasks = tmp_path / "tasks.json"
    _write_tasks(tasks)
    rc = skillopt.main(["optimize", str(skill), "--tasks", str(tasks),
                        "--iters", "2", "--reflector", "llm"])
    assert rc == 0
