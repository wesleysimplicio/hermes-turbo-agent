"""High-throughput async batch runner (Proposta F — OpenClaw best-of).

OpenClaw (Node.js + libuv) wins the "1000 async tasks" microbenchmark
because libuv's C event loop is faster than CPython's pure-Python
``asyncio``. This module closes the gap two ways:

1. Auto-detects ``uvloop`` (libuv binding for Python) and installs it as
   the event loop policy when available. uvloop closes the libuv gap to
   single-digit microseconds per task.
2. Provides a ``run_batch(jobs)`` helper that schedules N coroutines via
   ``asyncio.gather`` with bounded concurrency, returning a metrics
   snapshot the caller can log. This mirrors the OpenClaw "task batch"
   pattern that the upstream README benchmarks.

Pure stdlib by default; uvloop is an *optional* fast path. The fallback
remains the CPython asyncio policy so no install is required.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable, List, Optional, Sequence


@dataclass
class BatchMetrics:
    scheduled: int = 0
    completed: int = 0
    errored: int = 0
    elapsed_s: float = 0.0
    policy: str = "asyncio"

    @property
    def throughput_per_s(self) -> float:
        if self.elapsed_s <= 0:
            return 0.0
        return self.completed / self.elapsed_s

    def as_dict(self) -> dict[str, object]:
        return {
            "scheduled": self.scheduled,
            "completed": self.completed,
            "errored": self.errored,
            "elapsed_s": round(self.elapsed_s, 6),
            "throughput_per_s": round(self.throughput_per_s, 1),
            "policy": self.policy,
        }


@dataclass
class BatchResult:
    outputs: List[object] = field(default_factory=list)
    errors: List[BaseException] = field(default_factory=list)
    metrics: BatchMetrics = field(default_factory=BatchMetrics)


def install_uvloop_if_available() -> str:
    """Try to install the fastest available event-loop policy.

    Cross-platform resolution:
      1. ``uvloop`` (libuv binding for CPython) — best on Linux/macOS.
      2. ``winloop`` (drop-in uvloop replacement for Windows).
      3. ``asyncio`` fallback when neither is installed.

    Returns the chosen policy name. Safe to call multiple times — both
    libraries' ``install()`` calls are idempotent.
    """

    # Try uvloop first (Linux/macOS).
    try:
        import uvloop  # type: ignore[import-not-found]
    except ImportError:
        uvloop = None  # type: ignore[assignment]
    if uvloop is not None:
        try:
            uvloop.install()
            return "uvloop"
        except Exception:  # noqa: BLE001
            pass

    # Fall back to winloop (Windows port of uvloop).
    try:
        import winloop  # type: ignore[import-not-found]
    except ImportError:
        winloop = None  # type: ignore[assignment]
    if winloop is not None:
        try:
            winloop.install()
            return "winloop"
        except Exception:  # noqa: BLE001
            pass

    return "asyncio"


JobFactory = Callable[[int], Awaitable[object]]


async def _bounded_runner(
    factory: JobFactory,
    n: int,
    *,
    max_concurrency: int,
) -> BatchResult:
    sem = asyncio.Semaphore(max_concurrency)
    outputs: List[object] = [None] * n  # preallocate to keep order
    errors: List[BaseException] = []

    async def _one(i: int) -> None:
        async with sem:
            try:
                outputs[i] = await factory(i)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

    await asyncio.gather(*(_one(i) for i in range(n)))
    result = BatchResult(outputs=outputs, errors=errors)
    result.metrics.scheduled = n
    result.metrics.completed = n - len(errors)
    result.metrics.errored = len(errors)
    return result


def run_batch(
    factory: JobFactory,
    n: int,
    *,
    max_concurrency: int = 256,
    prefer_uvloop: bool = True,
) -> BatchResult:
    """Schedule ``n`` jobs and return the metrics snapshot.

    ``factory(i)`` produces the i-th coroutine — handy for benchmarks
    where the body is parameterised by index.
    """

    policy = (
        install_uvloop_if_available() if prefer_uvloop else "asyncio"
    )
    t0 = time.perf_counter()
    result = asyncio.run(_bounded_runner(factory, n, max_concurrency=max_concurrency))
    result.metrics.elapsed_s = time.perf_counter() - t0
    result.metrics.policy = policy
    return result


async def run_batch_async(
    factory: JobFactory,
    n: int,
    *,
    max_concurrency: int = 256,
) -> BatchResult:
    """Async variant for callers already inside an event loop."""

    t0 = time.perf_counter()
    result = await _bounded_runner(factory, n, max_concurrency=max_concurrency)
    result.metrics.elapsed_s = time.perf_counter() - t0
    try:
        import uvloop  # type: ignore[import-not-found]  # noqa: F401
        result.metrics.policy = "uvloop"
    except ImportError:
        try:
            import winloop  # type: ignore[import-not-found]  # noqa: F401
            result.metrics.policy = "winloop"
        except ImportError:
            result.metrics.policy = "asyncio"
    return result
