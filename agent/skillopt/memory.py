"""Optimizer-side memory: the rejected-edit buffer and the meta-skill.

Two pieces of state live with the *optimizer*, never in the deployed skill:

* :class:`RejectedEditBuffer` — recently gated-out edits. Feeding these back as
  negative examples stops the optimizer from re-proposing a direction the gate
  already punished (SkillOpt's "rejected edit buffer").
* :class:`MetaSkillMemory` — a rolling log of what helped and what hurt, scored.
  This is the "meta-skill memory": extended feedback for the optimizer that
  would only bloat the skill if it were deployed, so it is kept separate.
"""

from __future__ import annotations

from collections import deque
from typing import Deque, Iterable, List, Tuple

from .types import EditOp


class RejectedEditBuffer:
    """A bounded set of edit signatures the gate has rejected."""

    def __init__(self, maxlen: int = 32) -> None:
        self._order: Deque[str] = deque(maxlen=maxlen)
        self._ops: dict[str, EditOp] = {}

    def __len__(self) -> int:
        return len(self._order)

    def contains(self, op: EditOp) -> bool:
        return op.signature() in self._ops

    def add(self, op: EditOp) -> None:
        sig = op.signature()
        if sig in self._ops:
            return
        if len(self._order) == self._order.maxlen and self._order:
            evicted = self._order[0]
            # deque(maxlen) will drop the left item on append; mirror that here.
            self._ops.pop(evicted, None)
        self._order.append(sig)
        self._ops[sig] = op

    def extend(self, ops: Iterable[EditOp]) -> None:
        for op in ops:
            self.add(op)

    def filter(self, ops: Iterable[EditOp]) -> List[EditOp]:
        """Drop ops whose signature is already in the buffer."""

        return [op for op in ops if not self.contains(op)]

    def as_feedback(self, limit: int = 8) -> str:
        """Render recent rejects as text for the optimizer prompt."""

        recent = list(self._ops.values())[-limit:]
        if not recent:
            return ""
        lines = ["Previously rejected edits (do NOT repeat these directions):"]
        for op in recent:
            desc = op.content.strip() or op.target.strip()
            lines.append(f"- [{op.op}] {desc[:120]}")
        return "\n".join(lines)


class MetaSkillMemory:
    """Optimizer-side record of accepted/rejected edits and their scores."""

    def __init__(self, maxlen: int = 64) -> None:
        # Each entry: (accepted, delta, short_description)
        self._entries: Deque[Tuple[bool, float, str]] = deque(maxlen=maxlen)

    def __len__(self) -> int:
        return len(self._entries)

    def record_accept(self, ops: Iterable[EditOp], delta: float) -> None:
        for op in ops:
            self._entries.append((True, delta, self._describe(op)))

    def record_reject(self, ops: Iterable[EditOp], delta: float) -> None:
        for op in ops:
            self._entries.append((False, delta, self._describe(op)))

    @staticmethod
    def _describe(op: EditOp) -> str:
        body = op.content.strip() or op.target.strip()
        return f"[{op.op}] {body[:120]}"

    def render(self, limit: int = 10) -> str:
        """Text summary fed back to the optimizer between iterations."""

        if not self._entries:
            return ""
        wins = [e for e in self._entries if e[0]]
        losses = [e for e in self._entries if not e[0]]
        lines: List[str] = ["Meta-skill memory (optimizer notes):"]
        if wins:
            lines.append("What helped (validated by the gate):")
            for _, delta, desc in wins[-limit:]:
                lines.append(f"  + (+{delta:.3f}) {desc}")
        if losses:
            lines.append("What did not help (rejected by the gate):")
            for _, delta, desc in losses[-limit:]:
                lines.append(f"  - ({delta:+.3f}) {desc}")
        return "\n".join(lines)
