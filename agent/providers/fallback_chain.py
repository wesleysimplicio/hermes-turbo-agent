"""Provider fallback chain with jittered backoff.

Improves what upstream Hermes does:

    Upstream sets one provider per session. Rate-limit or 5xx from that
    provider = task fails or operator manually switches model.

This module wraps a chain of providers (cheap → backup → frontier) with:
  * Per-provider classification of which errors are *transient* (retry) vs
    *fatal* (skip to next provider).
  * Bounded jittered exponential backoff per provider.
  * Metrics: retries, switches, total wall time, which provider succeeded.

Pure stdlib. Synchronous + async variants share the same policy object.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Sequence, Tuple


@dataclass
class ProviderResult:
    """Whatever the provider returned plus a metadata layer."""

    response: object
    provider: str
    retries: int = 0
    elapsed_s: float = 0.0


ProviderCallable = Callable[[str], object]
AsyncProviderCallable = Callable[[str], Awaitable[object]]


_TRANSIENT_HINTS: Tuple[str, ...] = (
    "rate limit", "rate_limit", "429",
    "timeout", "timed out",
    "connection reset", "connection error",
    "server error", "500", "502", "503", "504",
    "overloaded",
)


def is_transient(exc: BaseException) -> bool:
    """Heuristic classifier for retry-vs-skip."""

    text = str(exc).lower()
    return any(hint in text for hint in _TRANSIENT_HINTS)


@dataclass
class ProviderChainMetrics:
    attempts: int = 0
    retries: int = 0
    switches: int = 0
    successes_per_provider: dict[str, int] = field(default_factory=dict)
    failures_per_provider: dict[str, int] = field(default_factory=dict)

    def record_success(self, provider: str, retries: int) -> None:
        self.attempts += 1
        self.retries += retries
        self.successes_per_provider[provider] = (
            self.successes_per_provider.get(provider, 0) + 1
        )

    def record_failure(self, provider: str) -> None:
        self.failures_per_provider[provider] = (
            self.failures_per_provider.get(provider, 0) + 1
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "attempts": self.attempts,
            "retries": self.retries,
            "switches": self.switches,
            "successes_per_provider": dict(self.successes_per_provider),
            "failures_per_provider": dict(self.failures_per_provider),
        }


@dataclass
class ProviderChain:
    """Try each provider in order with jittered exponential backoff.

    ``providers`` is a list of ``(name, callable)`` tuples. The chain stops
    at the first success and records which provider succeeded.

    Defaults: 3 retries per provider, base 0.5 s, max 8 s, full jitter.
    """

    providers: Sequence[Tuple[str, ProviderCallable]] = ()
    max_retries: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    metrics: ProviderChainMetrics = field(default_factory=ProviderChainMetrics)
    sleep: Callable[[float], None] = staticmethod(time.sleep)

    def _backoff(self, attempt: int) -> float:
        # Full jitter — AWS architecture blog recipe.
        d = min(self.max_delay_s, self.base_delay_s * (2 ** attempt))
        return random.uniform(0, d)

    def call(self, prompt: str) -> ProviderResult:
        if not self.providers:
            raise RuntimeError("ProviderChain has no providers configured")

        # Fast path: single provider + first-attempt success is the common
        # case. Avoid building exception state and ``time.perf_counter`` if
        # nothing went wrong.
        if len(self.providers) == 1:
            name, fn = self.providers[0]
            try:
                response = fn(prompt)
            except BaseException:  # noqa: BLE001
                return self._slow_call(prompt)
            self.metrics.attempts += 1
            self.metrics.successes_per_provider[name] = (
                self.metrics.successes_per_provider.get(name, 0) + 1
            )
            return ProviderResult(
                response=response, provider=name, retries=0, elapsed_s=0.0,
            )

        return self._slow_call(prompt)

    def _slow_call(self, prompt: str) -> ProviderResult:
        t0 = time.perf_counter()
        last_exc: Optional[BaseException] = None

        for i, (name, fn) in enumerate(self.providers):
            if i > 0:
                self.metrics.switches += 1
            for attempt in range(self.max_retries + 1):
                try:
                    response = fn(prompt)
                except BaseException as exc:  # noqa: BLE001
                    last_exc = exc
                    self.metrics.record_failure(name)
                    if not is_transient(exc):
                        break  # skip to next provider
                    if attempt < self.max_retries:
                        self.sleep(self._backoff(attempt))
                        continue
                    break  # exhausted retries; move on
                self.metrics.record_success(name, retries=attempt)
                return ProviderResult(
                    response=response, provider=name, retries=attempt,
                    elapsed_s=time.perf_counter() - t0,
                )

        assert last_exc is not None
        raise last_exc


@dataclass
class AsyncProviderChain:
    """Async variant of :class:`ProviderChain` for use under ``asyncio``."""

    providers: Sequence[Tuple[str, AsyncProviderCallable]] = ()
    max_retries: int = 3
    base_delay_s: float = 0.5
    max_delay_s: float = 8.0
    metrics: ProviderChainMetrics = field(default_factory=ProviderChainMetrics)

    def _backoff(self, attempt: int) -> float:
        d = min(self.max_delay_s, self.base_delay_s * (2 ** attempt))
        return random.uniform(0, d)

    async def call(self, prompt: str) -> ProviderResult:
        if not self.providers:
            raise RuntimeError("AsyncProviderChain has no providers configured")
        t0 = time.perf_counter()
        last_exc: Optional[BaseException] = None

        for i, (name, fn) in enumerate(self.providers):
            if i > 0:
                self.metrics.switches += 1
            for attempt in range(self.max_retries + 1):
                try:
                    response = await fn(prompt)
                except BaseException as exc:  # noqa: BLE001
                    last_exc = exc
                    self.metrics.record_failure(name)
                    if not is_transient(exc):
                        break
                    if attempt < self.max_retries:
                        await asyncio.sleep(self._backoff(attempt))
                        continue
                    break
                self.metrics.record_success(name, retries=attempt)
                return ProviderResult(
                    response=response, provider=name, retries=attempt,
                    elapsed_s=time.perf_counter() - t0,
                )

        assert last_exc is not None
        raise last_exc
