"""Tests for the rejected-edit buffer and meta-skill memory."""

from __future__ import annotations

from agent.skillopt.memory import MetaSkillMemory, RejectedEditBuffer
from agent.skillopt.types import EditOp


def _op(content: str) -> EditOp:
    return EditOp(op="add", content=content)


def test_rejected_buffer_contains_and_dedup() -> None:
    buf = RejectedEditBuffer()
    op = _op("- foo")
    buf.add(op)
    assert buf.contains(op)
    buf.add(op)  # dedup
    assert len(buf) == 1


def test_rejected_buffer_filter() -> None:
    buf = RejectedEditBuffer()
    buf.add(_op("- a"))
    kept = buf.filter([_op("- a"), _op("- b")])
    assert [o.content for o in kept] == ["- b"]


def test_rejected_buffer_eviction() -> None:
    buf = RejectedEditBuffer(maxlen=2)
    buf.add(_op("- a"))
    buf.add(_op("- b"))
    buf.add(_op("- c"))
    assert len(buf) == 2
    assert not buf.contains(_op("- a"))  # evicted
    assert buf.contains(_op("- c"))


def test_rejected_buffer_feedback_text() -> None:
    buf = RejectedEditBuffer()
    buf.add(_op("- avoid this"))
    fb = buf.as_feedback()
    assert "avoid this" in fb
    assert "rejected" in fb.lower()


def test_meta_memory_render_separates_wins_and_losses() -> None:
    meta = MetaSkillMemory()
    meta.record_accept([_op("- good step")], delta=0.1)
    meta.record_reject([_op("- bad step")], delta=-0.05)
    rendered = meta.render()
    assert "good step" in rendered
    assert "bad step" in rendered
    assert "helped" in rendered.lower()


def test_meta_memory_empty_render() -> None:
    assert MetaSkillMemory().render() == ""
