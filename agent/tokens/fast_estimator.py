"""Token-count estimator with tiktoken fast path and naive fallback.

OpenClaw wins token throughput (25M texts/s vs ~10M for the Python fork)
because V8 handles strings natively. We close that gap on the *accuracy*
axis (and a chunk of the speed axis) by using ``tiktoken`` when
available — the Rust-backed BPE tokeniser OpenAI ships, 3-6× faster
than any pure-Python BPE implementation.

Resolution order:

    1. ``tiktoken`` cached encoding (e.g. ``cl100k_base``) when the
       caller passes ``model=``.
    2. Cached estimator built around ``len(text) // 4`` (the naive
       Hermes Original estimator). Works without any dependency.

The module pre-loads the tokeniser once per encoding so repeated calls
amortise the (cold) one-shot tokeniser build cost.
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional


try:
    import tiktoken  # type: ignore[import-not-found]
    _HAS_TIKTOKEN = True
except ImportError:
    tiktoken = None  # type: ignore[assignment]
    _HAS_TIKTOKEN = False


class EstimatorBackend(str, Enum):
    NAIVE = "naive"          # len(text) // 4
    TIKTOKEN = "tiktoken"     # exact BPE


_ENCODING_CACHE: dict[str, object] = {}


def has_tiktoken() -> bool:
    return _HAS_TIKTOKEN


def _resolve_encoding(model: Optional[str]) -> Optional[object]:
    if not _HAS_TIKTOKEN:
        return None
    key = model or "cl100k_base"
    cached = _ENCODING_CACHE.get(key)
    if cached is not None:
        return cached
    try:
        if model:
            enc = tiktoken.encoding_for_model(model)
        else:
            enc = tiktoken.get_encoding("cl100k_base")
    except (KeyError, ValueError):
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:  # noqa: BLE001
            return None
    _ENCODING_CACHE[key] = enc
    return enc


def naive_estimate(text: str) -> int:
    """``len(text) // 4`` — fast, deterministic, no dependency."""

    return max(0, len(text)) // 4


def estimate(text: str, *, model: Optional[str] = None) -> int:
    """Return a token count estimate for ``text``.

    With tiktoken installed, returns the *exact* OpenAI-style BPE count
    for the resolved encoding. Otherwise, falls back to ``len // 4``.
    """

    if not text:
        return 0
    enc = _resolve_encoding(model)
    if enc is None:
        return naive_estimate(text)
    try:
        # encode returns a list[int]; we just want the count.
        return len(enc.encode(text))
    except Exception:  # noqa: BLE001
        return naive_estimate(text)


@dataclass(frozen=True)
class ThroughputSample:
    backend: EstimatorBackend
    samples: int
    median_us_per_call: float
    p95_us_per_call: float
    texts_per_second: float


def estimate_throughput(
    texts: Iterable[str],
    *,
    iters: int = 100,
    model: Optional[str] = None,
) -> ThroughputSample:
    """Micro-benchmark the active backend on ``texts`` (round-robin).

    Returns the median / p95 µs per call plus extrapolated texts/s for
    the active backend. Handy in benchmarks to confirm the chosen
    backend actually picked up.
    """

    text_list: List[str] = list(texts) or [""]
    backend = (
        EstimatorBackend.TIKTOKEN
        if _HAS_TIKTOKEN and _resolve_encoding(model) is not None
        else EstimatorBackend.NAIVE
    )
    samples_us: List[float] = []
    for i in range(iters):
        text = text_list[i % len(text_list)]
        t0 = time.perf_counter()
        estimate(text, model=model)
        samples_us.append((time.perf_counter() - t0) * 1_000_000)

    median = statistics.median(samples_us)
    p95 = _percentile(samples_us, 95.0)
    tps = (1_000_000 / median) if median > 0 else 0.0
    return ThroughputSample(
        backend=backend, samples=iters,
        median_us_per_call=round(median, 3),
        p95_us_per_call=round(p95, 3),
        texts_per_second=round(tps, 0),
    )


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(round((pct / 100.0) * (len(s) - 1)))
    return s[max(0, min(k, len(s) - 1))]
