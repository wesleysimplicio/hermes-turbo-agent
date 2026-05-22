"""Tests for the stage timing recorder (#82)."""

from __future__ import annotations

import time

from agent.telemetry.stage_timing import StageRecorder, format_run_report


class TestStageRecorder:
    def test_records_sample(self) -> None:
        r = StageRecorder()
        r.record("prompt_build", 12, provider="anthropic", model="claude-opus")
        assert len(r.samples) == 1
        assert r.samples[0].stage == "prompt_build"
        assert r.samples[0].elapsed_ms == 12
        assert r.samples[0].provider == "anthropic"

    def test_negative_clamped(self) -> None:
        r = StageRecorder()
        r.record("x", -3)
        assert r.samples[0].elapsed_ms == 0

    def test_context_manager_measures_time(self) -> None:
        r = StageRecorder()
        with r.stage("model_call", model="m"):
            time.sleep(0.005)
        assert len(r.samples) == 1
        assert r.samples[0].stage == "model_call"
        assert r.samples[0].elapsed_ms >= 0

    def test_aggregate_counts(self) -> None:
        r = StageRecorder()
        for ms in (10, 20, 30):
            r.record("call", ms)
        r.record("other", 5)
        agg = r.aggregate()
        assert agg["call"].samples == 3
        assert agg["call"].total_ms == 60
        assert agg["call"].min_ms == 10
        assert agg["call"].max_ms == 30
        assert abs(agg["call"].avg_ms - 20.0) < 0.01
        assert agg["other"].samples == 1

    def test_breakdown_by_provider(self) -> None:
        r = StageRecorder()
        r.record("model_call", 10, provider="anthropic")
        r.record("model_call", 20, provider="openai")
        r.record("model_call", 30, provider="anthropic")
        agg = r.breakdown_by("provider")
        assert agg["anthropic"].samples == 2
        assert agg["anthropic"].total_ms == 40
        assert agg["openai"].samples == 1

    def test_format_run_report_orders_by_total(self) -> None:
        r = StageRecorder()
        r.record("fast", 1)
        r.record("slow", 100)
        report = format_run_report(r)
        slow_idx = report.index("slow")
        fast_idx = report.index("fast")
        assert slow_idx < fast_idx

    def test_no_samples_does_not_crash(self) -> None:
        r = StageRecorder()
        assert "(no samples)" in format_run_report(r)
