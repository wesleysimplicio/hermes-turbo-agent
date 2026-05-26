"""Scoring primitives for ClawBench-style evaluation.

Three scorers, returning a float in [0.0, 1.0]:

- :func:`exact_match`  -- normalized string equality.
- :func:`soft_match`   -- Jaccard token overlap (case + punctuation insensitive).
- :func:`llm_judge_stub` -- deterministic placeholder for an LLM-as-judge call.
"""

from __future__ import annotations

import re
import string
from typing import Iterable

_PUNCT = str.maketrans("", "", string.punctuation)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().translate(_PUNCT)).strip()


def _tokens(text: str) -> set:
    return {t for t in _normalize(text).split(" ") if t}


def exact_match(output: str, expected: str) -> float:
    """Return 1.0 iff normalized strings are identical, else 0.0."""
    return 1.0 if _normalize(output) == _normalize(expected) else 0.0


def soft_match(output: str, expected: str) -> float:
    """Jaccard similarity on normalized token sets."""
    a, b = _tokens(output), _tokens(expected)
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def llm_judge_stub(output: str, expected: str) -> float:
    """Placeholder for an LLM-as-judge scorer.

    Returns the soft-match score so the harness can plug in a real judge later
    without changing call sites. Real implementations should call a graded
    judge model and parse a 0-1 rubric score.
    """
    return soft_match(output, expected)


_SCORERS = {
    "exact": exact_match,
    "soft": soft_match,
    "judge": llm_judge_stub,
}


def score(output: str, expected: str, mode: str = "exact") -> float:
    """Dispatch to a named scorer. Unknown modes fall back to exact."""
    return _SCORERS.get(mode, exact_match)(output, expected)


def available_scorers() -> Iterable[str]:
    return _SCORERS.keys()
