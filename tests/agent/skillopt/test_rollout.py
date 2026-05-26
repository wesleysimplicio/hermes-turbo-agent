"""Tests for the proxy rollout and overlap scoring."""

from __future__ import annotations

from agent.skillopt.rollout import OverlapRollout, f1_overlap, make_rollout
from agent.skillopt.types import Task


def test_f1_overlap_bounds() -> None:
    assert f1_overlap(set(), {"a"}) == 0.0
    assert f1_overlap({"a"}, set()) == 0.0
    assert f1_overlap({"a", "b"}, {"a", "b"}) == 1.0
    assert 0.0 < f1_overlap({"a", "b"}, {"a", "c"}) < 1.0


def test_overlap_rollout_success_when_skill_covers_reference() -> None:
    roll = OverlapRollout(success_threshold=0.5)
    task = Task(id="t", prompt="do thing", reference="validate inputs carefully")
    traj = roll(
        "# Skill\n\nAlways validate inputs carefully before doing thing.\n", task
    )
    assert traj.success
    assert traj.score > 0.5
    assert traj.feedback == ""  # no feedback needed on success


def test_overlap_rollout_failure_returns_reference_feedback() -> None:
    roll = OverlapRollout(success_threshold=0.9)
    task = Task(id="t", prompt="do thing", reference="esoteric unrelated terminology")
    traj = roll("# Skill\n\nNothing relevant here.\n", task)
    assert not traj.success
    assert traj.feedback == "esoteric unrelated terminology"


def test_make_rollout_factory() -> None:
    roll = make_rollout(success_threshold=0.7)
    assert isinstance(roll, OverlapRollout)
    assert roll.success_threshold == 0.7


def test_rollout_is_deterministic() -> None:
    roll = OverlapRollout()
    task = Task(id="t", prompt="p", reference="alpha beta gamma")
    a = roll("# S\n\nalpha beta\n", task)
    b = roll("# S\n\nalpha beta\n", task)
    assert a.score == b.score
    assert a.success == b.success
