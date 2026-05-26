"""Tests for the reflectors and edit-op parsing."""

from __future__ import annotations

from agent.skillopt.memory import MetaSkillMemory, RejectedEditBuffer
from agent.skillopt.reflect import (
    LLMReflector,
    LocalReflector,
    parse_edit_ops,
    tokenize,
)
from agent.skillopt.types import EditBudget, Trajectory


def test_tokenize_drops_stopwords_and_short() -> None:
    toks = tokenize("The agent should validate the schema carefully")
    assert "schema" in toks
    assert "validate" in toks
    assert "the" not in toks


def test_local_reflector_mines_missing_terms_from_failures() -> None:
    refl = LocalReflector(max_terms=3)
    failures = [
        Trajectory(task_id="t1", score=0.1, success=False,
                   feedback="must call validate_schema before commit"),
    ]
    ops = refl.propose("# Skill\n", [], failures, MetaSkillMemory(),
                       RejectedEditBuffer(), EditBudget())
    assert ops
    contents = " ".join(o.content for o in ops)
    assert "validate_schema" in contents or "commit" in contents
    assert all(o.op == "add" for o in ops)


def test_local_reflector_skips_terms_already_in_skill() -> None:
    refl = LocalReflector(max_terms=5)
    failures = [Trajectory(task_id="t1", score=0.1, success=False,
                           feedback="schema validation")]
    ops = refl.propose("# Skill\n\nschema validation is required\n", [],
                       failures, MetaSkillMemory(), RejectedEditBuffer(),
                       EditBudget())
    # Both salient terms are already present, so nothing to add.
    assert ops == []


def test_local_reflector_respects_rejected_buffer() -> None:
    refl = LocalReflector(max_terms=2)
    failures = [Trajectory(task_id="t1", score=0.1, success=False,
                           feedback="needs idempotency")]
    rejected = RejectedEditBuffer()
    first = refl.propose("# Skill\n", [], failures, MetaSkillMemory(),
                         rejected, EditBudget())
    assert first
    rejected.extend(first)
    second = refl.propose("# Skill\n", [], failures, MetaSkillMemory(),
                          rejected, EditBudget())
    assert second == []


def test_local_reflector_captures_success_pattern() -> None:
    refl = LocalReflector()
    successes = [
        Trajectory(task_id="t1", score=0.9, success=True, summary="ran tests first"),
        Trajectory(task_id="t2", score=0.9, success=True, summary="ran tests first"),
    ]
    ops = refl.propose("# Skill\n", successes, [], MetaSkillMemory(),
                       RejectedEditBuffer(), EditBudget())
    assert any("Proven" in o.section for o in ops)


def test_parse_edit_ops_plain_json() -> None:
    raw = '[{"op":"add","content":"- x","section":"S"},{"op":"delete","target":"y"}]'
    ops = parse_edit_ops(raw)
    assert len(ops) == 2
    assert ops[0].op == "add"
    assert ops[1].op == "delete"


def test_parse_edit_ops_with_fence_and_prose() -> None:
    raw = "Here are my edits:\n```json\n[{\"op\":\"add\",\"content\":\"- y\"}]\n```\nDone."
    ops = parse_edit_ops(raw)
    assert len(ops) == 1
    assert ops[0].content == "- y"


def test_parse_edit_ops_rejects_invalid() -> None:
    assert parse_edit_ops("not json") == []
    assert parse_edit_ops('[{"op":"add"}]') == []  # add with no content
    assert parse_edit_ops('[{"op":"bogus","content":"x"}]') == []


def test_llm_reflector_uses_completion() -> None:
    def fake_complete(prompt: str) -> str:
        assert "CURRENT SKILL" in prompt
        return '[{"op":"add","content":"- from llm","section":"Notes"}]'

    refl = LLMReflector(fake_complete)
    ops = refl.propose("# Skill\n", [], [], MetaSkillMemory(),
                       RejectedEditBuffer(), EditBudget())
    assert len(ops) == 1
    assert ops[0].content == "- from llm"


def test_llm_reflector_falls_back_on_error() -> None:
    def boom(prompt: str) -> str:
        raise RuntimeError("api down")

    failures = [Trajectory(task_id="t1", score=0.1, success=False,
                           feedback="missing rollback")]
    refl = LLMReflector(boom, fallback=LocalReflector())
    ops = refl.propose("# Skill\n", [], failures, MetaSkillMemory(),
                       RejectedEditBuffer(), EditBudget())
    # Fallback (local) still produces edits from the failure feedback.
    assert ops


def test_llm_reflector_falls_back_on_empty_parse() -> None:
    failures = [Trajectory(task_id="t1", score=0.1, success=False,
                           feedback="missing rollback")]
    refl = LLMReflector(lambda p: "no json here", fallback=LocalReflector())
    ops = refl.propose("# Skill\n", [], failures, MetaSkillMemory(),
                       RejectedEditBuffer(), EditBudget())
    assert ops
