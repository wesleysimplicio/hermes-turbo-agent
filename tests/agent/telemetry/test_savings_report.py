"""Unit tests for agent.telemetry.savings_report (issue #138)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from agent.telemetry import savings_report


def _rec(
    raw: int = 1000,
    comp: int = 500,
    *,
    adapter: str = "anthropic",
    tool: str = "read",
    ts: str | None = None,
) -> dict:
    return {
        "raw_tokens": raw,
        "compressed_tokens": comp,
        "saved_tokens": max(0, raw - comp),
        "adapter": adapter,
        "tool": tool,
        "command": "chat",
        "session": "s1",
        "repo": "r",
        "ts": ts or "2026-05-22T12:00:00Z",
        "savings_pct": round(100.0 * (raw - comp) / raw, 2) if raw else 0.0,
    }


def test_parse_since_supports_units():
    assert savings_report.parse_since("7d") == timedelta(days=7)
    assert savings_report.parse_since("24h") == timedelta(hours=24)
    assert savings_report.parse_since("2w") == timedelta(weeks=2)
    assert savings_report.parse_since("30m") == timedelta(minutes=30)


def test_parse_since_rejects_invalid_input():
    with pytest.raises(ValueError):
        savings_report.parse_since("forever")
    with pytest.raises(ValueError):
        savings_report.parse_since("d7")


def test_build_report_totals_and_pct():
    recs = [
        _rec(1000, 400),  # 600 saved
        _rec(2000, 1500),  # 500 saved
    ]
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report(recs, since=timedelta(days=7), now=now)

    assert report["totals"]["raw_tokens"] == 3000
    assert report["totals"]["saved_tokens"] == 1100
    assert report["totals"]["calls"] == 2
    # 1100/3000 = 36.67%
    assert report["totals"]["overall_savings_pct"] == pytest.approx(36.67, rel=1e-3)


def test_records_outside_window_are_dropped():
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    inside = _rec(ts="2026-05-22T01:00:00Z")
    outside = _rec(ts="2026-05-10T00:00:00Z")  # > 7d earlier
    report = savings_report.build_report(
        [inside, outside], since=timedelta(days=7), now=now
    )
    assert report["window"]["records"] == 1
    assert report["totals"]["raw_tokens"] == 1000


def test_records_without_timestamps_are_kept():
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    bad = {"raw_tokens": 100, "compressed_tokens": 0, "ts": ""}
    good = _rec(ts="2026-05-22T00:00:00Z")
    report = savings_report.build_report(
        [bad, good], since=timedelta(days=7), now=now
    )
    assert report["window"]["records"] == 2


def test_usd_cost_uses_adapter_price():
    recs = [
        _rec(2_000_000, 0, adapter="anthropic"),  # 2M saved tokens, $3/M default
        _rec(1_000_000, 0, adapter="openai"),     # 1M saved, $2.50/M default
    ]
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report(recs, since=timedelta(days=7), now=now)

    # 2M * 3.00 / 1M = $6.00; 1M * 2.50 / 1M = $2.50
    assert report["totals"]["estimated_usd_saved"] == pytest.approx(8.50, rel=1e-3)
    assert report["by_adapter"]["anthropic"]["usd"] == pytest.approx(6.0, rel=1e-3)
    assert report["by_adapter"]["openai"]["usd"] == pytest.approx(2.5, rel=1e-3)


def test_custom_prices_override_defaults():
    recs = [_rec(1_000_000, 0, adapter="anthropic")]
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report(
        recs, since=timedelta(days=7), now=now,
        prices={"anthropic": 10.0},
    )
    assert report["totals"]["estimated_usd_saved"] == pytest.approx(10.0)


def test_adapter_prefix_match_falls_back():
    recs = [_rec(1_000_000, 0, adapter="anthropic-claude-sonnet")]
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report(recs, since=timedelta(days=7), now=now)
    # Should still match "anthropic" prefix price
    assert report["by_adapter"]["anthropic-claude-sonnet"]["usd"] == pytest.approx(3.0)


def test_format_markdown_includes_totals_and_tables():
    recs = [
        _rec(1000, 200, adapter="anthropic", tool="read"),
        _rec(500, 100, adapter="openai", tool="grep"),
    ]
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report(recs, since=timedelta(days=7), now=now)
    md = savings_report.format_markdown(report)
    assert "Hermes Turbo" in md
    assert "Saved tokens" in md
    assert "anthropic" in md
    assert "## Top tools" in md


def test_format_text_handles_empty_log():
    now = datetime(2026, 5, 22, 13, 0, tzinfo=timezone.utc)
    report = savings_report.build_report([], since=timedelta(days=7), now=now)
    text = savings_report.format_text(report)
    assert "Records:           0" in text
    assert "Overall savings:   0.0%" in text


def test_cli_writes_json_to_out_file(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(_rec()) + "\n")
    out = tmp_path / "out.json"
    rc = savings_report.main([
        "--log", str(log),
        "--since", "30d",
        "--json",
        "--out", str(out),
    ])
    assert rc == 0
    parsed = json.loads(out.read_text())
    assert parsed["totals"]["raw_tokens"] == 1000


def test_cli_rejects_bad_since():
    rc = savings_report.main(["--since", "bogus"])
    assert rc == 2


def test_cli_handles_custom_prices_file(tmp_path: Path):
    log = tmp_path / "log.jsonl"
    log.write_text(json.dumps(_rec(1_000_000, 0, adapter="custom")) + "\n")
    prices = tmp_path / "prices.json"
    prices.write_text(json.dumps({"custom": 5.0}))
    out = tmp_path / "out.md"
    rc = savings_report.main([
        "--log", str(log),
        "--since", "30d",
        "--prices", str(prices),
        "--markdown",
        "--out", str(out),
    ])
    assert rc == 0
    # 1M tokens × $5/M = $5.00
    assert "5.0" in out.read_text()
