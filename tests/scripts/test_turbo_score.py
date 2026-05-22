"""Unit tests for ``scripts/turbo_score.py``."""

from __future__ import annotations

import json
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import turbo_score  # noqa: E402  (path tweak above)


def _report(metrics: dict) -> dict:
    return {"metrics": metrics}


def _metric(speedup: float | None) -> dict:
    return {"local": 1.0, "stock": speedup or 0, "speedup": speedup, "winner": "Tota"}


def test_compute_with_full_dataset_returns_a_score_between_0_and_100():
    report = _report({
        "async_1000_task_ms": _metric(1.5),
        "json_dumps_short_us": _metric(2.0),
        "tool_call_parse_us": _metric(1.2),
        "token_estimate_batch_us": _metric(3.0),
        "cold_start_ms": _metric(1.8),
    })
    baselines = {"memory_rss_mb": {"stock": 60, "local": 30}}
    turbo = turbo_score.compute(report, baselines, savings_pct=40.0)
    assert 0 <= turbo.score <= 100
    # all families present, none missing
    assert turbo.missing_families == ()
    assert len(turbo.families) == 5
    # token_savings at 40% → raw=0.8, weighted=16
    token_fam = next(f for f in turbo.families if f.name == "token_savings")
    assert abs(token_fam.raw_score - 0.8) < 1e-6


def test_missing_memory_and_savings_are_dropped_from_weight():
    report = _report({
        "async_1000_task_ms": _metric(1.0),
        "cold_start_ms": _metric(1.0),
    })
    turbo = turbo_score.compute(report, baselines={}, savings_pct=None)
    # latency, throughput, cold_start present; memory + token_savings missing
    assert "memory" in turbo.missing_families
    assert "token_savings" in turbo.missing_families
    family_names = {f.name for f in turbo.families}
    assert family_names == {"latency", "throughput", "cold_start"}


def test_tie_speedup_yields_midrange_score():
    report = _report({
        "async_1000_task_ms": _metric(1.0),
        "json_dumps_short_us": _metric(1.0),
        "tool_call_parse_us": _metric(1.0),
    })
    turbo = turbo_score.compute(report, baselines={}, savings_pct=None)
    latency = next(f for f in turbo.families if f.name == "latency")
    # speedup 1.0 → (1.0 - 0.5)/1.5 = 0.333..
    assert abs(latency.raw_score - (1.0 / 3.0)) < 1e-6


def test_regression_zeros_out_family():
    report = _report({
        # all heavy regressions
        "async_1000_task_ms": _metric(0.5),
        "json_dumps_short_us": _metric(0.5),
        "tool_call_parse_us": _metric(0.5),
    })
    turbo = turbo_score.compute(report, baselines={}, savings_pct=None)
    latency = next(f for f in turbo.families if f.name == "latency")
    assert latency.raw_score == 0.0


def test_blocked_metrics_are_skipped(tmp_path):
    report = _report({
        "async_1000_task_ms": {"local": None, "stock": None, "speedup": None,
                                "winner": "Blocked"},
        "json_dumps_short_us": _metric(2.0),
        "tool_call_parse_us": _metric(2.0),
    })
    turbo = turbo_score.compute(report, baselines={}, savings_pct=None)
    latency = next(f for f in turbo.families if f.name == "latency")
    assert latency.metric_count == 2  # blocked metric dropped


def test_markdown_output_includes_score_and_table():
    turbo = turbo_score.compute(
        _report({"async_1000_task_ms": _metric(1.5)}),
        baselines={},
        savings_pct=10.0,
    )
    md = turbo_score.format_markdown(turbo)
    assert "Turbo Score" in md
    assert "| Family |" in md
    assert "latency" in md


def test_text_output_has_breakdown_lines():
    turbo = turbo_score.compute(
        _report({"async_1000_task_ms": _metric(1.5)}),
        baselines={"memory_rss_mb": {"stock": 50, "local": 25}},
        savings_pct=20.0,
    )
    text = turbo_score.format_text(turbo)
    assert "Hermes Turbo Score" in text
    assert "latency" in text
    assert "memory" in text


def test_to_payload_round_trips_through_json():
    turbo = turbo_score.compute(
        _report({"async_1000_task_ms": _metric(2.0)}),
        baselines={},
        savings_pct=None,
    )
    payload = turbo_score.to_payload(turbo)
    json.dumps(payload)  # must be serializable
    assert payload["score"] == turbo.score
    assert isinstance(payload["families"], list)


def test_cli_writes_to_out_file(tmp_path: Path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_report({
        "async_1000_task_ms": _metric(1.5),
    })))
    baselines_path = tmp_path / "baselines.json"
    baselines_path.write_text(json.dumps({}))
    out_path = tmp_path / "out.json"
    rc = turbo_score.main([
        "--report", str(report_path),
        "--baselines", str(baselines_path),
        "--savings-pct", "0",
        "--json",
        "--out", str(out_path),
    ])
    assert rc == 0
    parsed = json.loads(out_path.read_text())
    assert "score" in parsed
    assert "families" in parsed


def test_default_baselines_file_loads():
    """The shipped docs/turbo-score-baselines.json must be valid JSON."""
    baselines = turbo_score._load_baselines(turbo_score.DEFAULT_BASELINES)
    assert isinstance(baselines, dict)
    if baselines:
        # at least the memory entry should be present so the family fires
        assert "memory_rss_mb" in baselines
