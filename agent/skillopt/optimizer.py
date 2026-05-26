"""The SkillOpt optimization loop: Rollout -> Reflect -> Edit -> Gate.

:class:`SkillOptimizer` keeps the model frozen and treats the skill document as
the trainable state. Each iteration:

1. **Rollout** — run a batch of training tasks under the *current* skill,
   producing scored trajectories split into success/failure batches.
2. **Reflect + Edit** — the reflector proposes bounded edits; the document
   applies them within the :class:`EditBudget` (the textual learning rate).
3. **Gate** — score the candidate on a held-out validation set; keep it only if
   it beats the incumbent by ``gate_margin``. Rejected edits feed the rejected
   buffer and the meta-skill memory so the optimizer learns from misses too.

Only ``best_skill`` is exported, matching SkillOpt's deployment story.
"""

from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional, Sequence

from .document import SkillDocument
from .memory import MetaSkillMemory, RejectedEditBuffer
from .reflect import LocalReflector, Reflector
from .types import (
    EditBudget,
    GateDecision,
    IterationLog,
    OptimizationResult,
    Task,
    Trajectory,
)

RolloutFn = Callable[[str, Task], Trajectory]


class SkillOptimizer:
    """Optimizes a skill document against held-out tasks with a frozen target."""

    def __init__(
        self,
        *,
        rollout_fn: RolloutFn,
        train_tasks: Sequence[Task],
        val_tasks: Sequence[Task],
        reflector: Optional[Reflector] = None,
        budget: Optional[EditBudget] = None,
        slow_budget: Optional[EditBudget] = None,
        gate_margin: float = 0.0,
        rollouts_per_iter: int = 0,
        slow_period: int = 3,
        seed: int = 0,
    ) -> None:
        if not val_tasks:
            raise ValueError("val_tasks must be non-empty (the gate needs a held-out set)")
        self.rollout_fn = rollout_fn
        self.train_tasks = list(train_tasks)
        self.val_tasks = list(val_tasks)
        self.reflector: Reflector = reflector or LocalReflector()
        self.budget = budget or EditBudget()
        # Slow updates: a wider budget applied after a run of validated wins,
        # letting the optimizer make broader, longer-horizon improvements once
        # a direction has proven safe.
        self.slow_budget = slow_budget or EditBudget(
            max_ops=self.budget.max_ops * 2,
            max_chars=self.budget.max_chars * 2,
        )
        self.gate_margin = gate_margin
        self.rollouts_per_iter = rollouts_per_iter or len(self.train_tasks)
        self.slow_period = max(1, slow_period)
        self._rng = random.Random(seed)

        self.rejected = RejectedEditBuffer()
        self.meta = MetaSkillMemory()
        self._eval_cache: Dict[str, float] = {}

    # ── gate ────────────────────────────────────────────────────────────────
    def evaluate(self, doc: SkillDocument) -> float:
        """Mean validation score of ``doc`` (cached by document text)."""

        cached = self._eval_cache.get(doc.text)
        if cached is not None:
            return cached
        scores = [self.rollout_fn(doc.text, t).score for t in self.val_tasks]
        mean = sum(scores) / len(scores) if scores else 0.0
        self._eval_cache[doc.text] = mean
        return mean

    def _gate(self, candidate: SkillDocument, incumbent_score: float) -> GateDecision:
        cand_score = self.evaluate(candidate)
        accepted = cand_score > incumbent_score + self.gate_margin
        return GateDecision(
            accepted=accepted,
            candidate_score=cand_score,
            incumbent_score=incumbent_score,
            margin=self.gate_margin,
        )

    # ── rollout ──────────────────────────────────────────────────────────────
    def _rollout_batch(self, skill_text: str) -> List[Trajectory]:
        if not self.train_tasks:
            return []
        k = min(self.rollouts_per_iter, len(self.train_tasks))
        batch = self._rng.sample(self.train_tasks, k)
        return [self.rollout_fn(skill_text, t) for t in batch]

    # ── main loop ─────────────────────────────────────────────────────────────
    def optimize(self, initial_skill: str, max_iters: int = 10) -> OptimizationResult:
        current = SkillDocument(initial_skill)
        best = current
        best_score = self.evaluate(current)
        initial_score = best_score

        history: List[IterationLog] = []
        consecutive_accepts = 0

        for it in range(max_iters):
            # 1) Rollout under the current skill.
            trajs = self._rollout_batch(current.text)
            successes = [t for t in trajs if t.success]
            failures = [t for t in trajs if not t.success]
            rollout_score = (
                sum(t.score for t in trajs) / len(trajs) if trajs else best_score
            )

            # Slow update: widen the budget after a streak of validated wins.
            slow = consecutive_accepts >= self.slow_period
            budget = self.slow_budget if slow else self.budget

            # 2) Reflect + Edit (bounded).
            proposed = self.reflector.propose(
                current.text, successes, failures, self.meta, self.rejected, budget
            )
            proposed = self.rejected.filter(proposed)
            candidate, apply_result = current.with_edits(proposed, budget)

            # 3) Gate on held-out validation.
            if apply_result.applied:
                decision = self._gate(candidate, best_score)
            else:
                # Nothing landed — no point re-scoring an identical document.
                decision = GateDecision(False, best_score, best_score, self.gate_margin)

            if decision.accepted:
                current = candidate
                best = candidate
                best_score = decision.candidate_score
                self.meta.record_accept(apply_result.applied, decision.delta)
                consecutive_accepts += 1
            else:
                # Reverting keeps the incumbent; record the miss as negative
                # feedback so the optimizer stops pushing this direction.
                self.rejected.extend(apply_result.applied)
                self.meta.record_reject(apply_result.applied, decision.delta)
                consecutive_accepts = 0

            history.append(
                IterationLog(
                    iteration=it,
                    rollout_score=rollout_score,
                    n_success=len(successes),
                    n_failure=len(failures),
                    proposed_edits=len(proposed),
                    applied_edits=len(apply_result.applied),
                    candidate_score=decision.candidate_score,
                    best_score=best_score,
                    accepted=decision.accepted,
                    slow_update=slow,
                )
            )

        return OptimizationResult(
            best_skill=best.text,
            best_score=best_score,
            initial_score=initial_score,
            iterations=len(history),
            history=history,
            meta_skill=self.meta.render(),
        )
