"""Thread-safe token-bucket rate limiter keyed by named tier.

Each tier (e.g. a delegation ``role``) gets its own independent token bucket:
tokens refill continuously based on elapsed wall-clock time, capped at a
burst capacity, and ``try_acquire`` consumes one token if available.

Used to gate the *rate* of an operation (e.g. subagent dispatch) over time,
complementing — not replacing — a separate concurrency cap. A concurrency
cap alone lets a model burn through its whole budget in a tight loop as long
as each call finishes quickly; this limiter bounds how often the gate opens
per minute regardless of how fast each call completes.
"""

from __future__ import annotations

import threading
import time
from typing import Dict, Optional


class _Bucket:
    __slots__ = ("tokens", "last_refill")

    def __init__(self, tokens: float, last_refill: float) -> None:
        self.tokens = tokens
        self.last_refill = last_refill


class TierRateLimiter:
    """Independent token buckets per named tier, created lazily on first use."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buckets: Dict[str, _Bucket] = {}

    def try_acquire(
        self,
        tier: str,
        rate_per_minute: float,
        capacity: Optional[float] = None,
    ) -> bool:
        """Attempt to consume one token from ``tier``'s bucket.

        ``rate_per_minute`` is read on every call, so a config change takes
        effect immediately without resetting the limiter. ``capacity``
        defaults to ``rate_per_minute`` (up to a full minute's burst), which
        matches the natural "N per minute" mental model.

        Returns ``True`` if a token was consumed (the caller may proceed),
        ``False`` if the tier is currently exhausted.
        """
        cap = capacity if capacity is not None else rate_per_minute
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(tier)
            if bucket is None:
                bucket = _Bucket(tokens=cap, last_refill=now)
                self._buckets[tier] = bucket
            elapsed = now - bucket.last_refill
            bucket.last_refill = now
            refill_per_second = rate_per_minute / 60.0
            bucket.tokens = min(cap, bucket.tokens + elapsed * refill_per_second)
            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True
            return False

    def reset(self, tier: Optional[str] = None) -> None:
        """Clear bucket state. Pass a tier name to reset only that tier."""
        with self._lock:
            if tier is None:
                self._buckets.clear()
            else:
                self._buckets.pop(tier, None)


__all__ = ["TierRateLimiter"]
