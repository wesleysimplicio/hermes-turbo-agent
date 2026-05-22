"""Tests for ``hermes_cli.web_perf`` (issue #137 web dashboard)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hermes_cli import web_perf


def test_stage_summary_handles_missing_log(monkeypatch, tmp_path: Path):
    from agent.telemetry import stage_timer
    monkeypatch.setattr(stage_timer, "get_log_path",
                        lambda: tmp_path / "missing.jsonl")
    out = web_perf.stage_summary()
    assert out["rows"] == []
    assert out["events"] == 0
    assert out["log_path"].endswith("missing.jsonl")


def test_stage_summary_rejects_bad_group_by():
    out = web_perf.stage_summary(group_by="bogus")
    assert out["rows"] == []
    assert "error" in out


def test_stage_summary_aggregates_real_log(monkeypatch, tmp_path: Path):
    from agent.telemetry import stage_timer
    log = tmp_path / "stage.jsonl"
    log.write_text(
        json.dumps({"stage": "compress", "duration_ms": 5.0, "ok": True}) + "\n"
        + json.dumps({"stage": "compress", "duration_ms": 7.0, "ok": True}) + "\n"
        + json.dumps({"stage": "router", "duration_ms": 2.0, "ok": True}) + "\n"
    )
    monkeypatch.setattr(stage_timer, "get_log_path", lambda: log)
    out = web_perf.stage_summary(group_by="stage")
    assert out["events"] == 3
    keys = {r["key"] for r in out["rows"]}
    assert keys == {"compress", "router"}


def test_token_savings_handles_empty_log(monkeypatch, tmp_path: Path):
    from agent.telemetry import token_savings as ts
    monkeypatch.setattr(ts, "default_log_path",
                        lambda: tmp_path / "missing.jsonl")
    out = web_perf.token_savings(since="7d")
    assert out["totals"]["raw_tokens"] == 0


def test_token_savings_rejects_bad_since():
    out = web_perf.token_savings(since="forever")
    assert "error" in out


def test_token_savings_reads_log(monkeypatch, tmp_path: Path):
    from agent.telemetry import token_savings as ts
    log = tmp_path / "savings.jsonl"
    log.write_text(json.dumps({
        "raw_tokens": 1000, "compressed_tokens": 200,
        "saved_tokens": 800,
        "adapter": "anthropic", "tool": "read",
        "ts": "2026-05-22T12:00:00Z",
    }) + "\n")
    monkeypatch.setattr(ts, "default_log_path", lambda: log)
    out = web_perf.token_savings(since="30d")
    assert out["totals"]["raw_tokens"] == 1000
    assert out["totals"]["saved_tokens"] == 800
    assert "anthropic" in out["by_adapter"]


def test_turbo_score_returns_payload():
    out = web_perf.turbo_score()
    # Either real payload or error; both are valid JSON-serializable.
    assert isinstance(out, dict)
    if "error" not in out:
        assert "score" in out
        assert "families" in out


def test_perf_html_injects_token():
    html = web_perf.perf_html(session_token="abc123")
    assert "abc123" in html
    assert "HERMES_SESSION_TOKEN" in html


def test_perf_html_without_token_is_plain():
    html = web_perf.perf_html(session_token="")
    # Token-injection prelude is absent (the JS reference to
    # window.HERMES_SESSION_TOKEN remains as a fallback).
    assert "window.HERMES_SESSION_TOKEN=" not in html
    assert "Hermes Turbo" in html


def test_register_adds_paths_to_public_set():
    # Use stub app to avoid fastapi requirement when not installed.
    class _StubApp:
        def __init__(self):
            self.routes = []

        def _factory(self, path):
            def deco(fn):
                self.routes.append((path, fn))
                return fn
            return deco

        def get(self, path):
            return self._factory(path)

    try:
        import fastapi  # noqa: F401
    except ImportError:
        pytest.skip("fastapi not available in this env")

    from fastapi import FastAPI
    app = FastAPI()
    public_paths: set[str] = set()
    web_perf.register(app, public_paths=public_paths)
    assert "/api/perf/stage_summary" in public_paths
    assert "/api/perf/token_savings" in public_paths
    assert "/api/perf/turbo_score" in public_paths


def test_register_endpoints_can_be_invoked_in_process(monkeypatch, tmp_path: Path):
    try:
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/httpx not available")

    from agent.telemetry import stage_timer, token_savings as ts
    monkeypatch.setattr(stage_timer, "get_log_path",
                        lambda: tmp_path / "stage.jsonl")
    monkeypatch.setattr(ts, "default_log_path",
                        lambda: tmp_path / "savings.jsonl")

    app = FastAPI()
    web_perf.register(app)
    client = TestClient(app)

    r = client.get("/api/perf/stage_summary")
    assert r.status_code == 200
    assert "rows" in r.json()

    r = client.get("/api/perf/token_savings?since=7d")
    assert r.status_code == 200
    assert "totals" in r.json()

    r = client.get("/api/perf/turbo_score")
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, dict)

    r = client.get("/perf")
    assert r.status_code == 200
    assert "Hermes Turbo" in r.text
