"""Rollout adapters: how the frozen target "runs" a task under a skill.

The optimizer is agnostic to *how* a rollout is produced — it just needs a
``rollout_fn(skill_text, task) -> Trajectory``. In production this wraps a real
frozen agent executing the task. For offline runs, CI, and the bundled CLI demo
we ship a deterministic proxy:

:class:`OverlapRollout` scores how well the skill equips the agent for a task by
measuring lexical overlap between the skill (plus the task prompt) and the
task's reference answer. A failing rollout returns the reference as feedback,
so the :class:`~agent.skillopt.reflect.LocalReflector` can mine the missing
terms and the loop genuinely improves the document over iterations.

This proxy is not a quality claim about real agents — it is a faithful, fully
reproducible stand-in for the rollout signal so the optimization machinery can
be exercised end to end without a model in the loop.
"""

from __future__ import annotations

from typing import Optional

from .reflect import tokenize
from .types import Task, Trajectory


def f1_overlap(predicted: set, reference: set) -> float:
    """Token-set F1 in ``[0, 1]`` (0 when either side is empty)."""

    if not predicted or not reference:
        return 0.0
    inter = len(predicted & reference)
    if inter == 0:
        return 0.0
    precision = inter / len(predicted)
    recall = inter / len(reference)
    return 2 * precision * recall / (precision + recall)


class OverlapRollout:
    """Deterministic proxy rollout based on skill/reference token overlap."""

    def __init__(self, success_threshold: float = 0.6) -> None:
        self.success_threshold = success_threshold

    def __call__(self, skill_text: str, task: Task) -> Trajectory:
        reference = task.reference or task.prompt
        ref_tokens = set(tokenize(reference))
        # The "agent" is equipped by whatever the skill and prompt cover.
        equipped = set(tokenize(skill_text)) | set(tokenize(task.prompt))
        score = f1_overlap(equipped, ref_tokens)
        success = score >= self.success_threshold
        # On failure, hand the grader's reference back as feedback so the
        # reflector can see exactly which terms were expected but missing.
        feedback = "" if success else reference
        return Trajectory(
            task_id=task.id,
            score=score,
            success=success,
            summary=f"covered {len(equipped & ref_tokens)}/{len(ref_tokens)} expected terms",
            feedback=feedback,
        )


def make_rollout(success_threshold: float = 0.6) -> OverlapRollout:
    """Factory for the default offline rollout."""

    return OverlapRollout(success_threshold=success_threshold)


def complete_via_auxiliary(model: Optional[str] = None):
    """Build a ``complete(prompt) -> str`` callable from Hermes' aux client.

    Returns ``None`` when no auxiliary model/credentials are configured, so
    callers can gracefully fall back to the deterministic reflector. Imports
    are deferred to keep this module import-light and offline-safe.
    """

    try:
        from agent.auxiliary_client import get_text_auxiliary_client  # type: ignore
    except Exception:
        return None

    try:
        client, default_model = get_text_auxiliary_client("skillopt")
    except Exception:
        return None

    resolved_model = model or default_model
    if client is None or not resolved_model:
        return None

    def _complete(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=resolved_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
        )
        return resp.choices[0].message.content or ""

    return _complete
