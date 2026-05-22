from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refresh_sync_benchmarks.py"


def load_module():
    spec = importlib.util.spec_from_file_location("refresh_sync_benchmarks_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["refresh_sync_benchmarks_test"] = module
    spec.loader.exec_module(module)
    return module


def test_build_delta_lines_marks_first_refresh():
    mod = load_module()
    current = {"metrics": {}}
    lines = mod.build_delta_lines(None, current)
    assert "First measured refresh" in lines[0]


def test_build_delta_lines_reports_direction():
    mod = load_module()
    previous = {
        "metrics": {
            "json_dumps_short_us": {
                "local": 5.0,
                "unit": "us",
                "lower_is_better": True
            }
        }
    }
    current = {
        "metrics": {
            "json_dumps_short_us": {
                "local": 4.0,
                "unit": "us",
                "lower_is_better": True
            }
        }
    }
    lines = mod.build_delta_lines(previous, current)
    assert "improved" in lines[0]
    assert "5.000 -> 4.000 us" in lines[0]


def test_build_pr_body_section_surfaces_stale_flag():
    mod = load_module()
    body = mod.build_pr_body_section(
        {
            "status": "failed",
            "generated_at": "2026-05-19T20:00:00+0000",
            "benchmark_json": "docs/hermes-turbo-benchmark-hermes-0.14.0.json",
            "benchmark_markdown": "docs/hermes-turbo-benchmark-hermes-0.14.0.md",
            "stale": True,
            "delta_lines": ["- refresh failed"],
            "error": "boom"
        }
    )
    assert "Stale claims: `True`" in body
    assert "boom" in body
