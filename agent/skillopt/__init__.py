"""SkillOpt — executive strategy for self-evolving agent skills.

A faithful, dependency-light implementation of Microsoft Research's SkillOpt
(https://microsoft.github.io/SkillOpt/). It optimizes a compact natural-language
*skill document* for a *frozen* language agent — the skill text is the trainable
state; model weights never change — via the loop:

    Rollout -> Reflect -> Edit -> Gate

with bounded edits (a "textual learning rate"), a rejected-edit buffer for
negative feedback, slow updates for validated long-horizon gains, meta-skill
memory on the optimizer side, and a held-out gate that only promotes
improvements. Only ``best_skill`` is exported.

Quick start::

    from agent.skillopt import SkillOptimizer, OverlapRollout, coerce_tasks

    tasks = coerce_tasks([{"id": "t1", "prompt": "...", "reference": "..."}])
    opt = SkillOptimizer(
        rollout_fn=OverlapRollout(),
        train_tasks=tasks,
        val_tasks=tasks,
    )
    result = opt.optimize("# My Skill\n", max_iters=10)
    print(result.best_skill, result.gain)
"""

from __future__ import annotations

from .document import SkillDocument
from .memory import MetaSkillMemory, RejectedEditBuffer
from .optimizer import SkillOptimizer
from .reflect import (
    LLMReflector,
    LocalReflector,
    Reflector,
    parse_edit_ops,
    tokenize,
)
from .rollout import OverlapRollout, complete_via_auxiliary, f1_overlap, make_rollout
from .types import (
    ApplyResult,
    EditBudget,
    EditOp,
    GateDecision,
    IterationLog,
    OptimizationResult,
    Task,
    Trajectory,
    coerce_tasks,
)

__all__ = [
    "SkillDocument",
    "SkillOptimizer",
    "Reflector",
    "LocalReflector",
    "LLMReflector",
    "OverlapRollout",
    "make_rollout",
    "complete_via_auxiliary",
    "f1_overlap",
    "tokenize",
    "parse_edit_ops",
    "MetaSkillMemory",
    "RejectedEditBuffer",
    "Task",
    "Trajectory",
    "EditOp",
    "EditBudget",
    "ApplyResult",
    "GateDecision",
    "IterationLog",
    "OptimizationResult",
    "coerce_tasks",
]
