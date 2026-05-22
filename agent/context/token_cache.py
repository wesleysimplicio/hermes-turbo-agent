"""Incremental token-estimate cache (issue #83).

Caches the token count of each conversation segment by a stable content
hash. Subsequent requests for the same segment avoid re-tokenizing,
which matters when the conversation grows append-only and the volatile
tail is small relative to the stable prefix.

Cache key is ``(model_id, blake2b(content))`` — invalidating by model
keeps us safe across tokenizer changes. Hits are recorded so the
telemetry layer can confirm savings vs. uncached estimation.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Callable, Optional, Tuple

Tokenizer = Callable[[str], int]


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    size: int

    @property
    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


class TokenEstimateCache:
    """Bounded LRU cache mapping ``(model, content_hash) -> token_count``.

    Safe to share across coroutines (RLock). Eviction is LRU; the cache
    never tries to hold the conversation in memory — it stores only an
    integer per segment.
    """

    def __init__(self, *, max_entries: int = 10_000) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._cap = max_entries
        self._lock = RLock()
        self._store: "OrderedDict[Tuple[str, str], int]" = OrderedDict()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash(content: str) -> str:
        return hashlib.blake2b(content.encode("utf-8", "replace"), digest_size=16).hexdigest()

    def stats(self) -> CacheStats:
        with self._lock:
            return CacheStats(hits=self._hits, misses=self._misses, size=len(self._store))

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def invalidate_model(self, model: str) -> int:
        """Drop every entry tied to ``model`` (e.g. tokenizer changed)."""
        removed = 0
        with self._lock:
            for key in list(self._store.keys()):
                if key[0] == model:
                    del self._store[key]
                    removed += 1
        return removed

    def get(self, content: str, *, model: str) -> Optional[int]:
        key = (model, self._hash(content))
        with self._lock:
            value = self._store.get(key)
            if value is None:
                self._misses += 1
                return None
            self._store.move_to_end(key)
            self._hits += 1
            return value

    def put(self, content: str, count: int, *, model: str) -> None:
        if count < 0:
            raise ValueError("count must be >= 0")
        key = (model, self._hash(content))
        with self._lock:
            if key in self._store:
                self._store.move_to_end(key)
                self._store[key] = count
                return
            self._store[key] = count
            if len(self._store) > self._cap:
                self._store.popitem(last=False)

    def estimate(
        self, content: str, *, model: str, tokenizer: Tokenizer
    ) -> int:
        """Return token count, computing only on miss."""
        cached = self.get(content, model=model)
        if cached is not None:
            return cached
        count = int(tokenizer(content))
        if count < 0:
            count = 0
        self.put(content, count, model=model)
        return count


def incremental_total(
    segments: list[str],
    *,
    model: str,
    tokenizer: Tokenizer,
    cache: TokenEstimateCache,
) -> int:
    """Sum token counts segment-by-segment, leveraging the cache."""
    return sum(cache.estimate(seg, model=model, tokenizer=tokenizer) for seg in segments)
