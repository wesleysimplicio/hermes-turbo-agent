"""Core data types for SkillOpt.

SkillOpt (https://microsoft.github.io/SkillOpt/) optimizes a compact
natural-language *skill document* for a frozen language agent. The skill text
is the trainable state; the model weights never change. The loop is

    Rollout -> Reflect -> Edit -> Gate

and these dataclasses are the values that flow between those stages:

* :class:`Task`        — one unit of work the frozen target attempts.
* :class:`Trajectory`  — the scored outcome of a rollout.
* :class:`EditOp`      — a single bounded add/delete/replace on the skill.
* :class:`EditBudget`  — the "textual learning rate" cap on edits per step.
* :class:`ApplyResult` — what actually landed vs. what the budget dropped.
* :class:`IterationLog`/:class:`OptimizationResult` — observability.

Everything here is plain stdlib so the engine imports with zero side effects.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence, Tuple


@dataclass(frozen=True)
class Task:
    """A single task the frozen target model attempts during a rollout."""

    id: str
    prompt: str
    reference: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Trajectory:
    """The scored result of running one :class:`Task` under a skill.

    ``score`` is normalised to ``[0, 1]``; ``success`` is the gate-relevant
    boolean (typically ``score >= threshold``). ``feedback`` carries the
    natural-language signal the optimizer reflects on — an error message, a
    grader rationale, or the expected answer.
    """

    task_id: str
    score: float
    success: bool
    summary: str = ""
    feedback: str = ""
    messages: Tuple[str, ...] = ()
    tool_calls: Tuple[str, ...] = ()


@dataclass(frozen=True)
class EditOp:
    """A bounded edit to the skill document.

    ``op`` is one of ``"add"``, ``"delete"`` or ``"replace"``:

    * ``add``     — insert ``content`` (under ``section`` when given).
    * ``delete``  — remove the first block matching ``target``.
    * ``replace`` — swap the first block matching ``target`` for ``content``.

    ``rationale`` is optimizer-side only and never written into the skill.
    """

    op: str
    content: str = ""
    section: str = ""
    target: str = ""
    rationale: str = ""

    def normalized(self) -> "EditOp":
        return EditOp(
            op=self.op.strip().lower(),
            content=self.content,
            section=self.section.strip(),
            target=self.target,
            rationale=self.rationale.strip(),
        )

    def cost(self) -> int:
        """Character cost charged against the per-iteration budget."""

        return len(self.content) + len(self.target)

    def signature(self) -> str:
        """Stable identity used to dedupe and to key the rejected buffer."""

        op = self.op.strip().lower()
        return "\x1f".join(
            (op, self.section.strip(), self.content.strip(), self.target.strip())
        )


@dataclass(frozen=True)
class EditBudget:
    """The "textual learning rate": how far the skill may drift per step.

    A small budget keeps updates stable and reversible (few ops, few chars);
    a large budget enables the broader "slow updates" once a direction has
    been validated. ``min_score_floor`` lets a caller forbid edits that would
    shrink the document below a sanity size (guards against destructive
    delete storms).
    """

    max_ops: int = 3
    max_chars: int = 600

    def __post_init__(self) -> None:
        if self.max_ops < 0 or self.max_chars < 0:
            raise ValueError("budget limits must be non-negative")


@dataclass(frozen=True)
class ApplyResult:
    """Outcome of applying a list of edits under a budget."""

    text: str
    applied: Tuple[EditOp, ...] = ()
    skipped: Tuple[EditOp, ...] = ()
    chars_changed: int = 0


@dataclass(frozen=True)
class GateDecision:
    """Held-out validation verdict for a candidate skill."""

    accepted: bool
    candidate_score: float
    incumbent_score: float
    margin: float

    @property
    def delta(self) -> float:
        return self.candidate_score - self.incumbent_score


@dataclass(frozen=True)
class IterationLog:
    """One row of the optimization trace."""

    iteration: int
    rollout_score: float
    n_success: int
    n_failure: int
    proposed_edits: int
    applied_edits: int
    candidate_score: float
    best_score: float
    accepted: bool
    slow_update: bool = False


@dataclass
class OptimizationResult:
    """Final report returned by :meth:`SkillOptimizer.optimize`."""

    best_skill: str
    best_score: float
    initial_score: float
    iterations: int
    history: List[IterationLog] = field(default_factory=list)
    meta_skill: str = ""

    @property
    def gain(self) -> float:
        return self.best_score - self.initial_score

    @property
    def accepted_iterations(self) -> int:
        return sum(1 for row in self.history if row.accepted)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_score": round(self.best_score, 6),
            "initial_score": round(self.initial_score, 6),
            "gain": round(self.gain, 6),
            "iterations": self.iterations,
            "accepted_iterations": self.accepted_iterations,
            "history": [
                {
                    "iteration": row.iteration,
                    "rollout_score": round(row.rollout_score, 6),
                    "n_success": row.n_success,
                    "n_failure": row.n_failure,
                    "proposed_edits": row.proposed_edits,
                    "applied_edits": row.applied_edits,
                    "candidate_score": round(row.candidate_score, 6),
                    "best_score": round(row.best_score, 6),
                    "accepted": row.accepted,
                    "slow_update": row.slow_update,
                }
                for row in self.history
            ],
        }


def coerce_tasks(raw: Sequence[Any]) -> List[Task]:
    """Build :class:`Task` objects from dicts or strings (loader convenience)."""

    tasks: List[Task] = []
    for i, item in enumerate(raw):
        if isinstance(item, Task):
            tasks.append(item)
        elif isinstance(item, Mapping):
            tasks.append(
                Task(
                    id=str(item.get("id", f"task-{i}")),
                    prompt=str(item.get("prompt", "")),
                    reference=str(item.get("reference", "")),
                    metadata=dict(item.get("metadata", {}) or {}),
                )
            )
        else:
            tasks.append(Task(id=f"task-{i}", prompt=str(item)))
    return tasks
