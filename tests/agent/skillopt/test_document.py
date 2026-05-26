"""Tests for the bounded-edit skill document."""

from __future__ import annotations

from agent.skillopt.document import SkillDocument
from agent.skillopt.types import EditBudget, EditOp


def test_add_appends_block_when_no_section() -> None:
    doc = SkillDocument("# Title\n\nbody\n")
    result = doc.bounded_apply([EditOp(op="add", content="new bullet")])
    assert "new bullet" in result.text
    assert len(result.applied) == 1
    assert result.text.endswith("new bullet\n")


def test_add_into_existing_section() -> None:
    doc = SkillDocument("# Title\n\n## Checklist\n\n- one\n\n## Other\n\nx\n")
    result = doc.bounded_apply(
        [EditOp(op="add", content="- two", section="Checklist")]
    )
    # The new bullet lands inside Checklist, before the Other heading.
    checklist_idx = result.text.index("- two")
    other_idx = result.text.index("## Other")
    assert checklist_idx < other_idx


def test_add_creates_missing_section() -> None:
    doc = SkillDocument("# Title\n\nbody\n")
    result = doc.bounded_apply(
        [EditOp(op="add", content="- item", section="Pitfalls")]
    )
    assert "## Pitfalls" in result.text
    assert "- item" in result.text


def test_add_skips_duplicate_content() -> None:
    doc = SkillDocument("# Title\n\n- existing\n")
    result = doc.bounded_apply([EditOp(op="add", content="- existing")])
    assert result.applied == ()
    assert len(result.skipped) == 1


def test_replace_swaps_target() -> None:
    doc = SkillDocument("# Title\n\nold line\n")
    result = doc.bounded_apply(
        [EditOp(op="replace", target="old line", content="new line")]
    )
    assert "new line" in result.text
    assert "old line" not in result.text


def test_replace_missing_target_is_skipped() -> None:
    doc = SkillDocument("# Title\n\nbody\n")
    result = doc.bounded_apply(
        [EditOp(op="replace", target="absent", content="x")]
    )
    assert result.applied == ()
    assert len(result.skipped) == 1


def test_delete_removes_block() -> None:
    doc = SkillDocument("# Title\n\nkeep\n\nremove me\n")
    result = doc.bounded_apply([EditOp(op="delete", target="remove me")])
    assert "remove me" not in result.text
    assert "keep" in result.text


def test_budget_limits_number_of_ops() -> None:
    doc = SkillDocument("# Title\n")
    ops = [EditOp(op="add", content=f"- item {i}") for i in range(5)]
    result = doc.bounded_apply(ops, EditBudget(max_ops=2, max_chars=10_000))
    assert len(result.applied) == 2
    assert len(result.skipped) == 3


def test_budget_limits_chars() -> None:
    doc = SkillDocument("# Title\n")
    # Distinct 100-char blocks (distinct so dedup doesn't drop them).
    ops = [EditOp(op="add", content=f"{i:03d}-" + "x" * 96) for i in range(5)]
    result = doc.bounded_apply(ops, EditBudget(max_ops=99, max_chars=250))
    # Each op costs 100 chars, so only 2 fit under 250.
    assert len(result.applied) == 2


def test_with_edits_returns_new_document() -> None:
    doc = SkillDocument("# Title\n")
    new_doc, result = doc.with_edits([EditOp(op="add", content="- x")])
    assert new_doc is not doc
    assert new_doc.version == doc.version + 1
    assert "- x" in new_doc.text
    assert "- x" not in doc.text  # original untouched


def test_unknown_op_is_skipped() -> None:
    doc = SkillDocument("# Title\n")
    result = doc.bounded_apply([EditOp(op="frobnicate", content="x")])
    assert result.applied == ()


def test_normalization_trailing_newline() -> None:
    doc = SkillDocument("# Title\n\n\n\nbody\n\n\n")
    assert doc.text.endswith("body\n")
    assert not doc.text.endswith("\n\n")
