"""Tests for ``agent.telemetry.gain_analytics``."""

from __future__ import annotations

import json
from pathlib import Path

from agent.telemetry import gain_analytics


SAMPLE = [
    {"raw_tokens": 1000, "compressed_tokens": 200, "saved_tokens": 800,
     "tool": "read_file", "adapter": "anthropic", "ts": "2026-05-20T10:00:00Z"},
    {"raw_tokens": 500, "compressed_tokens": 100, "saved_tokens": 400,
     "tool": "grep", "adapter": "anthropic", "ts": "2026-05-20T11:00:00Z"},
    {"raw_tokens": 2000, "compressed_tokens": 800, "saved_tokens": 1200,
     "tool": "read_file", "adapter": "gemini", "ts": "2026-05-21T09:00:00Z"},
    {"raw_tokens": 100, "compressed_tokens": 90, "saved_tokens": 10,
     "tool": "bash", "adapter": "gemini", "ts": "2026-05-21T12:00:00Z"},
]


def test_aggregate_totals() -> None:
    agg = gain_analytics.aggregate(SAMPLE)
    assert agg["records"] == 4
    assert agg["total_raw_tokens"] == 3600
    assert agg["total_saved_tokens"] == 2410
    assert agg["overall_savings_pct"] == round(100 * 2410 / 3600, 2)


def test_top_wasteful_tools_and_limit() -> None:
    agg = gain_analytics.aggregate(SAMPLE)
    top = gain_analytics.top_wasteful_tools(agg, limit=2)
    assert top[0] == ("read_file", 3000, 2000)
    assert top[1][0] == "grep"
    assert gain_analytics.top_wasteful_tools(agg, limit=0) == []


def test_trend_sorted_by_day() -> None:
    days = gain_analytics.trend(gain_analytics.aggregate(SAMPLE))
    assert [d for d, _, _ in days] == ["2026-05-20", "2026-05-21"]
    assert days[0][1] == 1500 and days[1][1] == 2100


def test_aggregate_handles_dirty_records() -> None:
    agg = gain_analytics.aggregate([
        {"raw_tokens": "bad", "compressed_tokens": 10, "ts": None},
        {"raw_tokens": 100, "compressed_tokens": 25},
    ])
    assert agg["records"] == 2 and agg["total_raw_tokens"] == 100


def test_run_text_and_json(tmp_path: Path, capsys) -> None:
    log = tmp_path / "s.jsonl"
    with log.open("w", encoding="utf-8") as fh:
        for rec in SAMPLE:
            fh.write(json.dumps(rec) + "\n")
    assert gain_analytics.run(["--log", str(log), "--top", "2"]) == 0
    txt = capsys.readouterr().out
    assert "Token Savings Report" in txt and "read_file" in txt and "2026-05-20" in txt
    assert gain_analytics.run(["--log", str(log), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_raw_tokens"] == 3600 and "by_tool" in payload


def test_run_missing_log_is_empty(tmp_path: Path, capsys) -> None:
    assert gain_analytics.run(["--log", str(tmp_path / "absent.jsonl"), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records"] == 0 and payload["total_saved_tokens"] == 0
