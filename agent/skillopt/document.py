"""The trainable skill document and its bounded edit semantics.

A :class:`SkillDocument` wraps the markdown body of a skill. It is treated as
the *trainable state*: the optimizer proposes :class:`~agent.skillopt.types.EditOp`
operations, and :meth:`SkillDocument.bounded_apply` lands them within an
:class:`~agent.skillopt.types.EditBudget` (the "textual learning rate").

Edits are intentionally coarse — add/delete/replace whole blocks — because the
unit a frozen agent actually reads is a paragraph or a bullet, not a character.
Applying an edit returns a *new* document, so a candidate can be validated by
the gate without disturbing the incumbent.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .types import ApplyResult, EditBudget, EditOp

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _normalize(text: str) -> str:
    """Collapse trailing whitespace and guarantee a single trailing newline."""

    body = text.replace("\r\n", "\n").replace("\r", "\n").rstrip("\n")
    return body + "\n" if body else ""


class SkillDocument:
    """A markdown skill body that supports bounded add/delete/replace edits."""

    def __init__(self, text: str, name: str = "skill") -> None:
        self.name = name
        self._text = _normalize(text)
        self.version = 0

    # ── basics ────────────────────────────────────────────────────────────
    @property
    def text(self) -> str:
        return self._text

    def char_count(self) -> int:
        return len(self._text)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, SkillDocument) and other._text == self._text

    def __hash__(self) -> int:
        return hash(self._text)

    # ── single-op application (pure, returns new text) ──────────────────────
    def _apply_add(self, text: str, op: EditOp) -> Optional[str]:
        content = op.content.strip("\n")
        if not content:
            return None
        # Don't add a block that is already present verbatim — keeps the loop
        # from re-proposing the same line forever and inflating the document.
        if content in text:
            return None

        if not op.section:
            joiner = "\n\n" if text.strip() else ""
            return _normalize(text + joiner + content)

        lines = text.split("\n")
        insert_at = self._section_end(lines, op.section)
        if insert_at is None:
            # Section doesn't exist yet: create it at the end of the document.
            block = f"\n## {op.section}\n\n{content}\n"
            return _normalize(text.rstrip("\n") + "\n" + block)
        lines[insert_at:insert_at] = ["", content]
        return _normalize("\n".join(lines))

    def _apply_replace(self, text: str, op: EditOp) -> Optional[str]:
        target = op.target.strip("\n")
        if not target or target not in text:
            return None
        return _normalize(text.replace(target, op.content.strip("\n"), 1))

    def _apply_delete(self, text: str, op: EditOp) -> Optional[str]:
        target = op.target.strip("\n")
        if not target or target not in text:
            return None
        # Remove the block plus any blank line it leaves behind.
        replaced = text.replace(target + "\n", "", 1)
        if replaced == text:
            replaced = text.replace(target, "", 1)
        return _normalize(re.sub(r"\n{3,}", "\n\n", replaced))

    def _apply_one(self, text: str, op: EditOp) -> Optional[str]:
        op = op.normalized()
        if op.op == "add":
            return self._apply_add(text, op)
        if op.op == "replace":
            return self._apply_replace(text, op)
        if op.op == "delete":
            return self._apply_delete(text, op)
        return None

    @staticmethod
    def _section_end(lines: List[str], section: str) -> Optional[int]:
        """Index just past the last content line of ``section`` (else None)."""

        target = section.strip().lower().lstrip("#").strip()
        start: Optional[int] = None
        start_level = 0
        for i, line in enumerate(lines):
            m = _HEADING_RE.match(line)
            if not m:
                continue
            heading = m.group(2).strip().lower()
            if heading == target:
                start = i
                start_level = len(m.group(1))
                break
        if start is None:
            return None
        # Walk to the next heading of the same-or-shallower level.
        end = len(lines)
        for j in range(start + 1, len(lines)):
            m = _HEADING_RE.match(lines[j])
            if m and len(m.group(1)) <= start_level:
                end = j
                break
        # Trim trailing blank lines inside the section.
        while end - 1 > start and not lines[end - 1].strip():
            end -= 1
        return end

    # ── bounded multi-op application (the public entry point) ───────────────
    def bounded_apply(
        self, ops: List[EditOp], budget: Optional[EditBudget] = None
    ) -> ApplyResult:
        """Apply ``ops`` in order, honouring ``budget`` (the textual LR).

        Ops that would exceed ``max_ops`` or ``max_chars``, or that are no-ops
        against the current text (e.g. a delete whose target is absent), are
        reported in :attr:`ApplyResult.skipped` rather than applied.
        """

        budget = budget or EditBudget()
        text = self._text
        applied: List[EditOp] = []
        skipped: List[EditOp] = []
        chars = 0

        for op in ops:
            if len(applied) >= budget.max_ops:
                skipped.append(op)
                continue
            cost = op.cost()
            if chars + cost > budget.max_chars:
                skipped.append(op)
                continue
            new_text = self._apply_one(text, op)
            if new_text is None or new_text == text:
                skipped.append(op)
                continue
            text = new_text
            chars += cost
            applied.append(op)

        return ApplyResult(
            text=text,
            applied=tuple(applied),
            skipped=tuple(skipped),
            chars_changed=chars,
        )

    def with_edits(
        self, ops: List[EditOp], budget: Optional[EditBudget] = None
    ) -> Tuple["SkillDocument", ApplyResult]:
        """Return a *new* document with ``ops`` applied, plus the apply result."""

        result = self.bounded_apply(ops, budget)
        doc = SkillDocument(result.text, name=self.name)
        doc.version = self.version + 1
        return doc, result
