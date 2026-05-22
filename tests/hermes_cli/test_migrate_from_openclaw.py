"""Tests for ``hermes_cli.migrate_openclaw`` (issue #139)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from hermes_cli import migrate_openclaw


class _Args:
    """Minimal argparse-like namespace."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


def test_detect_openclaw_returns_false_when_missing(tmp_path: Path):
    detected, version = migrate_openclaw._detect_openclaw(tmp_path / "nope")
    assert detected is False
    assert version is None


def test_detect_openclaw_reads_version_file(tmp_path: Path):
    src = tmp_path / ".openclaw"
    src.mkdir()
    (src / "VERSION").write_text("1.2.3\n")
    detected, version = migrate_openclaw._detect_openclaw(src)
    assert detected is True
    assert version == "1.2.3"


def test_detect_openclaw_reads_package_json(tmp_path: Path):
    src = tmp_path / ".openclaw"
    src.mkdir()
    (src / "package.json").write_text(json.dumps({"version": "2.0.0"}))
    detected, version = migrate_openclaw._detect_openclaw(src)
    assert detected is True
    assert version == "2.0.0"


def test_detect_openclaw_handles_malformed_package_json(tmp_path: Path):
    src = tmp_path / ".openclaw"
    src.mkdir()
    (src / "package.json").write_text("not json")
    detected, version = migrate_openclaw._detect_openclaw(src)
    assert detected is True
    assert version is None


def test_run_benchmark_records_blocked_when_no_openclaw(tmp_path: Path):
    report = migrate_openclaw.run_benchmark(
        tmp_path / ".nothing", migrated=False, dry_run=True,
    )
    assert report.openclaw_detected is False
    assert any("not found" in n for n in report.notes)
    # always emits the two probes
    probe_names = {p.name for p in report.hermes_probes}
    assert "cold_start_ms" in probe_names
    assert "token_savings_pct" in probe_names


def test_format_benchmark_markdown_renders_sections(tmp_path: Path):
    report = migrate_openclaw.run_benchmark(
        tmp_path / ".nothing", migrated=True, dry_run=False,
    )
    md = migrate_openclaw.format_benchmark_markdown(report)
    assert "OpenClaw Migration Benchmark" in md
    assert "OpenClaw baseline (published)" in md
    assert "Hermes Turbo probes" in md
    # Turbo Score table should render against the shipped baselines/report
    assert "Turbo Score" in md


def test_format_benchmark_markdown_includes_turbo_score_when_available(tmp_path: Path):
    report = migrate_openclaw.run_benchmark(
        tmp_path / ".nothing", migrated=True, dry_run=False,
    )
    md = migrate_openclaw.format_benchmark_markdown(report)
    if report.turbo_score is not None:
        assert "Turbo Score:" in md
    else:
        assert "Turbo Score unavailable" in md


def test_migrate_command_calls_claw_then_benchmark(monkeypatch, tmp_path: Path):
    called = {"claw": 0}

    def fake_claw_command(args):
        called["claw"] += 1
        called["action"] = getattr(args, "claw_action", None)

    from hermes_cli import claw as claw_mod
    monkeypatch.setattr(claw_mod, "claw_command", fake_claw_command)

    out_file = tmp_path / "bench.md"
    args = _Args(
        source=str(tmp_path / ".nope"),
        dry_run=True,
        benchmark=True,
        benchmark_out=out_file,
    )
    rc = migrate_openclaw.migrate_from_openclaw_command(args)
    assert rc == 0
    assert called["claw"] == 1
    assert called["action"] == "migrate"
    assert out_file.exists()
    assert "OpenClaw Migration Benchmark" in out_file.read_text()


def test_migrate_command_skips_benchmark_when_flag_off(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        "hermes_cli.claw.claw_command",
        lambda args: None,
    )
    args = _Args(
        source=str(tmp_path / ".nope"),
        dry_run=True,
        benchmark=False,
    )
    rc = migrate_openclaw.migrate_from_openclaw_command(args)
    assert rc == 0


def test_migrate_command_propagates_claw_systemexit(monkeypatch, tmp_path: Path):
    def boom(args):
        raise SystemExit(2)

    monkeypatch.setattr("hermes_cli.claw.claw_command", boom)
    args = _Args(
        source=str(tmp_path / ".nope"),
        dry_run=True,
        benchmark=False,
    )
    rc = migrate_openclaw.migrate_from_openclaw_command(args)
    assert rc == 2
