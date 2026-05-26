"""Tests for ``agent.tracing.spans`` (Proposta D)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent.tracing import (
    Span,
    SpanRecorder,
    SpanStatus,
    set_default_recorder,
    span,
)


@pytest.fixture()
def recorder(monkeypatch: pytest.MonkeyPatch) -> SpanRecorder:
    r = SpanRecorder()
    set_default_recorder(r)
    return r


def test_records_basic_span(recorder: SpanRecorder) -> None:
    with span("router.decide", attributes={"text": "hi"}) as s:
        s.set_attribute("matched", True)
    spans = recorder.snapshot()
    assert len(spans) == 1
    s = spans[0]
    assert s.name == "router.decide"
    assert s.status == SpanStatus.OK
    assert s.attributes == {"text": "hi", "matched": True}
    assert s.elapsed_us >= 0


def test_nested_spans_share_trace_id_and_chain_parent(
    recorder: SpanRecorder,
) -> None:
    with span("outer") as outer:
        with span("inner") as inner:
            pass
    spans = recorder.snapshot()
    assert len(spans) == 2
    inner_s = next(s for s in spans if s.name == "inner")
    outer_s = next(s for s in spans if s.name == "outer")
    assert inner_s.trace_id == outer_s.trace_id
    assert inner_s.parent_span_id == outer_s.span_id
    assert outer_s.parent_span_id is None


def test_error_span_status(recorder: SpanRecorder) -> None:
    with pytest.raises(RuntimeError):
        with span("boom"):
            raise RuntimeError("kaboom")
    spans = recorder.snapshot()
    assert spans[0].status == SpanStatus.ERROR
    assert "kaboom" in (spans[0].error_message or "")


def test_jsonl_export(tmp_path: Path) -> None:
    log = tmp_path / "spans.jsonl"
    r = SpanRecorder(jsonl_path=str(log))
    with span("export.test", recorder=r):
        pass
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["name"] == "export.test"
    assert data["status"] == "OK"


def test_to_dict_schema() -> None:
    s = Span(name="x", trace_id="t", span_id="s", start_ns=1_000_000_000,
             end_ns=1_000_500_000)
    s.set_attribute("k", "v")
    s.status = SpanStatus.OK
    d = s.to_dict()
    for key in ("name", "trace_id", "span_id", "parent_span_id",
                "start_ns", "end_ns", "elapsed_us", "status",
                "error_message", "attributes"):
        assert key in d
    assert d["elapsed_us"] == 500.0
