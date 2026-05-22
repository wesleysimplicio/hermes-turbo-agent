"""Stdlib TF-IDF relevance scorer for picking cold refs to expand.

Pure ``math`` + ``collections.Counter`` -- no numpy / sklearn. Ranks a
small corpus of handles against a query so the agent can decide which
cold ref to ``expand``.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


@dataclass(frozen=True)
class ScoredHandle:
    key: str
    score: float


class RelevanceScorer:
    """TF-IDF cosine scorer over a small corpus of handle summaries."""

    def __init__(self, corpus: Mapping[str, str]) -> None:
        self._docs: dict[str, Counter[str]] = {
            k: Counter(_tokenize(text)) for k, text in corpus.items()
        }
        n = max(1, len(self._docs))
        df: Counter[str] = Counter()
        for d in self._docs.values():
            df.update(d.keys())
        self._idf = {t: math.log((1 + n) / (1 + c)) + 1.0 for t, c in df.items()}
        self._norms = {
            k: math.sqrt(sum((f * self._idf.get(t, 0.0)) ** 2
                             for t, f in tf.items())) or 1.0
            for k, tf in self._docs.items()
        }

    def score(self, query: str, *, top_k: int | None = None) -> list[ScoredHandle]:
        q_tf = Counter(_tokenize(query))
        if not q_tf:
            return []
        q_vec = {t: f * self._idf.get(t, 0.0) for t, f in q_tf.items()}
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        ranked: list[ScoredHandle] = []
        for key, tf in self._docs.items():
            dot = sum(qw * tf[t] * self._idf.get(t, 0.0)
                      for t, qw in q_vec.items() if t in tf)
            if dot:
                ranked.append(ScoredHandle(key, dot / (q_norm * self._norms[key])))
        ranked.sort(key=lambda h: h.score, reverse=True)
        return ranked[:top_k] if top_k is not None else ranked

    def best(self, query: str) -> ScoredHandle | None:
        r = self.score(query, top_k=1)
        return r[0] if r else None

    @classmethod
    def from_pairs(cls, pairs: Sequence[tuple[str, str]]) -> "RelevanceScorer":
        return cls(dict(pairs))
