"""Content-hash keyed LRU token-count cache.

Tokenization is hot on the request path: every turn re-estimates the cost of
the same system prompt, the same skill docs, the same prior assistant turns.
This module memoizes ``len(tokenize(content))`` by ``(tokenizer_key, hash)``
so the second call is a dict lookup.

Cache safety:
- Keys include a ``tokenizer_key`` (model name or tokenizer fingerprint).
  Switching tokenizer never returns a stale count.
- Content is hashed with SHA-256; collisions are not a practical concern.
- Bounded by ``maxsize``; oldest entries are evicted (LRU).
- Cleared on ``invalidate()`` or ``invalidate(tokenizer_key=...)``.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from typing import Callable, Optional


def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


class TokenCache:
    """Bounded LRU cache: (tokenizer_key, content_hash) -> token_count."""

    def __init__(self, maxsize: int = 4096) -> None:
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self._maxsize = maxsize
        self._data: "OrderedDict[tuple, int]" = OrderedDict()
        self._hits = 0
        self._misses = 0

    def count(
        self,
        content: str,
        tokenizer_key: str,
        compute: Callable[[str], int],
    ) -> int:
        """Return cached count or compute, store, and return it."""
        key = (tokenizer_key, _content_hash(content))
        cached = self._data.get(key)
        if cached is not None:
            self._data.move_to_end(key)
            self._hits += 1
            return cached
        self._misses += 1
        value = int(compute(content))
        self._data[key] = value
        self._data.move_to_end(key)
        if len(self._data) > self._maxsize:
            self._data.popitem(last=False)
        return value

    def invalidate(self, tokenizer_key: Optional[str] = None) -> int:
        """Drop entries. With ``tokenizer_key``, drop only that bucket."""
        if tokenizer_key is None:
            n = len(self._data)
            self._data.clear()
            return n
        to_drop = [k for k in self._data if k[0] == tokenizer_key]
        for k in to_drop:
            self._data.pop(k, None)
        return len(to_drop)

    def stats(self) -> dict:
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total else 0.0
        return {
            "size": len(self._data),
            "maxsize": self._maxsize,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }

    def __len__(self) -> int:
        return len(self._data)
