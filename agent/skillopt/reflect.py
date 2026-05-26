"""Reflectors: the "optimizer model" that turns rollouts into edits.

SkillOpt's *Reflect* + *Edit* stages run on a separate optimizer that reads the
success and failure batches independently and proposes bounded edits. This
module provides two implementations behind one small protocol:

* :class:`LocalReflector` — deterministic, dependency-free. It mines the terms a
  failing rollout was graded against but the skill never mentioned, and proposes
  small checklist additions. Good for offline runs, CI, and as a fallback.
* :class:`LLMReflector` — wraps any ``complete(prompt) -> str`` callable (e.g. a
  frozen optimizer LLM) and parses a JSON edit list out of the completion.

Both honour the rejected-edit buffer and read the meta-skill memory, so the
negative-feedback and extended-feedback signals are wired through either path.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import List, Optional, Protocol, Sequence

from .memory import MetaSkillMemory, RejectedEditBuffer
from .types import EditBudget, EditOp, Trajectory

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9_+\-]{2,}")

_STOPWORDS = frozenset(
    """
    the a an and or but if then else for to of in on at by with from into as is
    are was were be been being this that these those it its you your we our they
    them he she his her not no yes do does did done can could should would will
    shall may might must have has had get got make made use used using when what
    which who whom where why how all any each both more most other some such only
    own same so than too very just about above after again against because before
    below between during over under up down out off here there ensure cover step
    """.split()
)


def tokenize(text: str) -> List[str]:
    """Lowercase content tokens with stopwords and short fragments removed."""

    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


class Reflector(Protocol):
    """Proposes edits from the current skill and the latest rollout batch."""

    def propose(
        self,
        skill_text: str,
        successes: Sequence[Trajectory],
        failures: Sequence[Trajectory],
        meta: MetaSkillMemory,
        rejected: RejectedEditBuffer,
        budget: EditBudget,
    ) -> List[EditOp]:
        ...


class LocalReflector:
    """Heuristic reflector — no model required, fully deterministic.

    Failure analysis dominates: it finds graded-against terms the skill is
    missing and proposes them as checklist bullets, one per op so the edit
    budget controls how many land per iteration (the textual learning rate in
    action). Successes contribute at most one "proven step" note.
    """

    def __init__(self, max_terms: int = 6, checklist_section: str = "Checklist") -> None:
        self.max_terms = max_terms
        self.checklist_section = checklist_section

    def propose(
        self,
        skill_text: str,
        successes: Sequence[Trajectory],
        failures: Sequence[Trajectory],
        meta: MetaSkillMemory,
        rejected: RejectedEditBuffer,
        budget: EditBudget,
    ) -> List[EditOp]:
        skill_tokens = set(tokenize(skill_text))
        ops: List[EditOp] = []

        # ── failure batch: surface terms the skill never covered ───────────
        missing: Counter[str] = Counter()
        for traj in failures:
            signal = traj.feedback or traj.summary
            for tok in tokenize(signal):
                if tok not in skill_tokens:
                    missing[tok] += 1
        for term, _count in missing.most_common(self.max_terms):
            ops.append(
                EditOp(
                    op="add",
                    content=f"- Cover: {term}",
                    section=self.checklist_section,
                    rationale="missing term observed across failing rollouts",
                )
            )

        # ── success batch: capture a recurring proven step ─────────────────
        if successes:
            summaries = Counter(
                t.summary.strip() for t in successes if t.summary.strip()
            )
            if summaries:
                phrase, _ = summaries.most_common(1)[0]
                if phrase and phrase not in skill_text:
                    ops.append(
                        EditOp(
                            op="add",
                            content=f"- Proven: {phrase}",
                            section="Proven Steps",
                            rationale="pattern recurring across successful rollouts",
                        )
                    )

        return rejected.filter(ops)


class LLMReflector:
    """Reflector backed by a frozen optimizer LLM.

    ``complete`` takes a fully-rendered prompt and returns the model's text.
    The text must contain a JSON array of edit objects; anything around the
    array is tolerated. On any parse failure the reflector yields no edits,
    which the optimizer treats as a skipped iteration (safe no-op).
    """

    def __init__(self, complete, fallback: Optional[Reflector] = None) -> None:
        self._complete = complete
        self._fallback = fallback or LocalReflector()

    def propose(
        self,
        skill_text: str,
        successes: Sequence[Trajectory],
        failures: Sequence[Trajectory],
        meta: MetaSkillMemory,
        rejected: RejectedEditBuffer,
        budget: EditBudget,
    ) -> List[EditOp]:
        prompt = self.build_prompt(
            skill_text, successes, failures, meta, rejected, budget
        )
        try:
            raw = self._complete(prompt)
        except Exception:
            return self._fallback.propose(
                skill_text, successes, failures, meta, rejected, budget
            )
        ops = parse_edit_ops(raw or "")
        if not ops:
            return self._fallback.propose(
                skill_text, successes, failures, meta, rejected, budget
            )
        return rejected.filter(ops)

    @staticmethod
    def build_prompt(
        skill_text: str,
        successes: Sequence[Trajectory],
        failures: Sequence[Trajectory],
        meta: MetaSkillMemory,
        rejected: RejectedEditBuffer,
        budget: EditBudget,
    ) -> str:
        def _batch(label: str, trajs: Sequence[Trajectory]) -> str:
            if not trajs:
                return f"{label}: (none)"
            rows = []
            for t in trajs[:8]:
                fb = (t.feedback or t.summary).strip().replace("\n", " ")
                rows.append(f"- score={t.score:.2f} :: {fb[:240]}")
            return f"{label}:\n" + "\n".join(rows)

        parts = [
            "You optimize a natural-language SKILL document for a frozen agent.",
            "Analyze the SUCCESS and FAILURE batches independently, then propose "
            "a SMALL set of edits that would raise held-out task performance.",
            "",
            f"Edit budget (textual learning rate): at most {budget.max_ops} edits "
            f"and {budget.max_chars} changed characters this round. Stay reversible.",
            "",
            "Return ONLY a JSON array. Each element is one of:",
            '  {"op":"add","section":"<heading>","content":"<text>","rationale":"<why>"}',
            '  {"op":"replace","target":"<exact existing text>","content":"<new text>"}',
            '  {"op":"delete","target":"<exact existing text>"}',
            "",
            "=== CURRENT SKILL ===",
            skill_text.strip(),
            "",
            "=== ROLLOUTS ===",
            _batch("SUCCESS batch", successes),
            _batch("FAILURE batch", failures),
        ]
        meta_text = meta.render()
        if meta_text:
            parts += ["", "=== " + meta_text]
        rej_text = rejected.as_feedback()
        if rej_text:
            parts += ["", "=== " + rej_text]
        parts += ["", "JSON edits:"]
        return "\n".join(parts)


def parse_edit_ops(raw: str) -> List[EditOp]:
    """Extract a JSON edit array from model output and build EditOps."""

    text = raw.strip()
    if "```" in text:
        # Strip the first fenced block's fences if present.
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    try:
        data = json.loads(text[start : end + 1])
    except (json.JSONDecodeError, ValueError):
        return []
    if not isinstance(data, list):
        return []

    ops: List[EditOp] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        op = str(item.get("op", "")).strip().lower()
        if op not in {"add", "delete", "replace"}:
            continue
        content = str(item.get("content", "") or "")
        target = str(item.get("target", "") or "")
        if op == "add" and not content.strip():
            continue
        if op in {"delete", "replace"} and not target.strip():
            continue
        ops.append(
            EditOp(
                op=op,
                content=content,
                section=str(item.get("section", "") or ""),
                target=target,
                rationale=str(item.get("rationale", "") or ""),
            )
        )
    return ops
