"""Tests for the SkillOpt optimization loop."""

from __future__ import annotations

import pytest

from agent.skillopt.optimizer import SkillOptimizer
from agent.skillopt.reflect import LocalReflector
from agent.skillopt.rollout import OverlapRollout
from agent.skillopt.types import EditBudget, EditOp, Task, Trajectory


def _tasks():
    return [
        Task(id="t1", prompt="write a function",
             reference="validate inputs handle errors return value cleanly"),
        Task(id="t2", prompt="parse a file",
             reference="open file parse contents close handle errors gracefully"),
    ]


def test_requires_val_tasks() -> None:
    with pytest.raises(ValueError):
        SkillOptimizer(rollout_fn=OverlapRollout(), train_tasks=_tasks(), val_tasks=[])


def test_offline_loop_improves_deficient_skill() -> None:
    tasks = _tasks()
    opt = SkillOptimizer(
        rollout_fn=OverlapRollout(success_threshold=0.95),
        train_tasks=tasks,
        val_tasks=tasks,
        budget=EditBudget(max_ops=3, max_chars=2000),
        seed=1,
    )
    result = opt.optimize("# Skill\n\nA bare skill with little guidance.\n", max_iters=12)
    assert result.gain > 0
    assert result.best_score >= result.initial_score
    # The improved skill picked up terms from the references.
    assert "validate" in result.best_skill or "errors" in result.best_skill


def test_best_score_is_monotonic_nondecreasing() -> None:
    tasks = _tasks()
    opt = SkillOptimizer(
        rollout_fn=OverlapRollout(success_threshold=0.95),
        train_tasks=tasks,
        val_tasks=tasks,
        seed=3,
    )
    result = opt.optimize("# Skill\n", max_iters=10)
    best_seq = [row.best_score for row in result.history]
    assert best_seq == sorted(best_seq)


def test_gate_rejects_non_improving_edits() -> None:
    tasks = _tasks()

    class NoiseReflector:
        """Always proposes an edit irrelevant to the references."""

        def propose(self, skill_text, successes, failures, meta, rejected, budget):
            return [EditOp(op="add", content="- zzz irrelevant qqq")]

    opt = SkillOptimizer(
        rollout_fn=OverlapRollout(success_threshold=0.95),
        train_tasks=tasks,
        val_tasks=tasks,
        reflector=NoiseReflector(),
        gate_margin=0.0,
        seed=0,
    )
    result = opt.optimize("# Skill\n", max_iters=4)
    # Irrelevant edits never raise the validation score, so none are accepted
    # and the rejected buffer fills up.
    assert result.accepted_iterations == 0
    assert result.gain == 0
    assert len(opt.rejected) >= 1


def test_no_op_iteration_does_not_crash() -> None:
    tasks = _tasks()

    class SilentReflector:
        def propose(self, *a, **k):
            return []

    opt = SkillOptimizer(
        rollout_fn=OverlapRollout(),
        train_tasks=tasks,
        val_tasks=tasks,
        reflector=SilentReflector(),
    )
    result = opt.optimize("# Skill\n", max_iters=3)
    assert result.accepted_iterations == 0
    assert all(row.applied_edits == 0 for row in result.history)


def test_slow_update_widens_budget_after_streak() -> None:
    tasks = _tasks()

    def scoring_rollout(skill_text, task):
        # Score rises monotonically with the number of GOOD markers, so each
        # added marker is a genuine validated improvement.
        return Trajectory(
            task_id=task.id,
            score=min(1.0, skill_text.count("GOOD") * 0.1),
            success=False,
        )

    class AddGood:
        def __init__(self):
            self.n = 0

        def propose(self, skill_text, successes, failures, meta, rejected, budget):
            self.n += 1
            return [EditOp(op="add", content=f"GOOD marker {self.n}")]

    opt = SkillOptimizer(
        rollout_fn=scoring_rollout,
        train_tasks=tasks,
        val_tasks=tasks,
        reflector=AddGood(),
        slow_period=2,
        seed=0,
    )
    result = opt.optimize("# Skill\n", max_iters=4)
    # Two consecutive validated accepts flip the loop into slow-update mode.
    assert any(row.slow_update for row in result.history)
    assert result.accepted_iterations >= 3


def test_result_to_dict_is_serializable() -> None:
    import json

    tasks = _tasks()
    opt = SkillOptimizer(rollout_fn=OverlapRollout(), train_tasks=tasks, val_tasks=tasks)
    result = opt.optimize("# Skill\n", max_iters=2)
    payload = result.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["iterations"] == 2
    assert "history" in payload


def test_evaluate_is_cached() -> None:
    tasks = _tasks()
    calls = {"n": 0}

    def counting_rollout(skill_text, task):
        calls["n"] += 1
        return Trajectory(task_id=task.id, score=0.5, success=False)

    opt = SkillOptimizer(
        rollout_fn=counting_rollout,
        train_tasks=tasks,
        val_tasks=tasks,
        reflector=LocalReflector(),
    )
    from agent.skillopt.document import SkillDocument

    doc = SkillDocument("# x\n")
    opt.evaluate(doc)
    n_after_first = calls["n"]
    opt.evaluate(doc)  # cached — no new rollout calls
    assert calls["n"] == n_after_first
