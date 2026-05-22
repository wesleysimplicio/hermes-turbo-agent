#!/usr/bin/env python3
"""Lean segmented benchmark: only the customisations that beat upstream.

Post-mortem cleanup retired every turbo module that performed worse than the
naïve upstream-equivalent baseline. What remains:

    1. project_mapping  (P1)  — 36×–39× vs tree walk
    2. routing          (#99) — 174×–185× vs LLM proxy
    3. receipts         (P7)  — parity (~1×) with md5; value is cache hit rate

Run::

    python scripts/benchmark_full_turbo_segments.py
    python scripts/benchmark_full_turbo_segments.py --iters 1000
    python scripts/benchmark_full_turbo_segments.py --json --out report.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class StageResult:
    segment: str
    name: str
    iters: int
    median_us: float
    p95_us: float
    baseline_us: Optional[float] = None
    notes: str = ""

    @property
    def speedup(self) -> Optional[float]:
        if self.baseline_us is None or self.median_us <= 0:
            return None
        return round(self.baseline_us / self.median_us, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment": self.segment,
            "name": self.name,
            "iters": self.iters,
            "median_us": round(self.median_us, 2),
            "p95_us": round(self.p95_us, 2),
            "baseline_us": (
                round(self.baseline_us, 2) if self.baseline_us is not None else None
            ),
            "speedup_x": self.speedup,
            "notes": self.notes,
        }


def _time_us(fn: Callable[[], object], iters: int) -> Tuple[float, float]:
    samples: List[float] = []
    for _ in range(iters):
        t0 = time.perf_counter()
        fn()
        samples.append((time.perf_counter() - t0) * 1_000_000)
    return statistics.median(samples), _percentile(samples, 95.0)


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = int(round((pct / 100.0) * (len(s) - 1)))
    return s[max(0, min(k, len(s) - 1))]


# ---- project_mapping ----------------------------------------------------- #


def _bench_project_mapping(iters: int) -> List[StageResult]:
    from agent.project_mapper import detect_fingerprint

    def _naive_tree_walk(root: Path) -> Dict[str, int]:
        counters: Dict[str, int] = {}
        for path in root.rglob("*"):
            if path.is_file() and path.suffix:
                counters[path.suffix] = counters.get(path.suffix, 0) + 1
            if sum(counters.values()) > 5000:
                break
        return counters

    detect_fingerprint(ROOT)
    med, p95 = _time_us(lambda: detect_fingerprint(ROOT), iters)
    base, _ = _time_us(lambda: _naive_tree_walk(ROOT), max(1, iters // 5))
    return [StageResult(
        "project_mapping",
        "detect_fingerprint (manifest heuristics)",
        iters, med, p95, baseline_us=base,
        notes="reads top-level manifests; baseline walks the tree.",
    )]


# ---- routing ------------------------------------------------------------- #


def _bench_routing(iters: int) -> List[StageResult]:
    from agent.router.deterministic import DeterministicRouter, RouteRule

    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello|oi|olá)$", lambda _t, _m: "hello back",
    ))
    router.add_rule(RouteRule.from_regex(
        "time", r"^what (is|'s) the time\??$",
        lambda _t, _m: {"tool": "now", "args": {}},
    ))

    def _baseline_llm_proxy() -> str:
        time.sleep(0.0001)  # 100 µs — conservative LLM stand-in
        return "llm-response"

    m, p = _time_us(lambda: router.route("hi"), iters)
    b, _ = _time_us(_baseline_llm_proxy, max(1, iters // 10))
    return [StageResult(
        "routing", "DeterministicRouter.route",
        iters, m, p, baseline_us=b,
        notes="regex skips LLM round-trip entirely on trivial intents.",
    )]


# ---- receipts ------------------------------------------------------------ #


def _bench_receipts(iters: int, tmp_dir: Path) -> List[StageResult]:
    from agent.telemetry.receipts import content_hash, lookup_receipt, record_receipt

    payload = "rm -rf /tmp/nothing"
    record_receipt(payload=payload, tokens=10, directory=tmp_dir)

    m_hash, p_hash = _time_us(lambda: content_hash(payload), iters)
    import hashlib
    b_hash, _ = _time_us(
        lambda: hashlib.md5(payload.encode()).hexdigest(), iters,
    )

    m_lookup, p_lookup = _time_us(
        lambda: lookup_receipt(payload, tmp_dir), max(1, iters // 5),
    )

    return [
        StageResult(
            "receipts", "content_hash (sha256)",
            iters, m_hash, p_hash, baseline_us=b_hash,
            notes="content-addressable; parity with md5.",
        ),
        StageResult(
            "receipts", "lookup_receipt (cache hit, disk)",
            max(1, iters // 5), m_lookup, p_lookup, baseline_us=None,
            notes="net-new: short-circuits re-execution on hash hit.",
        ),
    ]


# ---- orchestration ------------------------------------------------------- #


def run_all(iters: int) -> List[StageResult]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        results: List[StageResult] = []
        results.extend(_bench_project_mapping(iters))
        results.extend(_bench_routing(iters))
        results.extend(_bench_receipts(iters, tmp_dir))
    return results


def _format_table(results: List[StageResult]) -> str:
    name_w = max(len(r.name) for r in results)
    seg_w = max(len(r.segment) for r in results)
    rows = [
        f"{'segment'.ljust(seg_w)}  {'stage'.ljust(name_w)}  "
        f"{'p50_us':>9}  {'p95_us':>9}  {'baseline':>11}  {'speedup':>9}"
    ]
    rows.append("-" * len(rows[0]))
    last_segment = None
    for r in results:
        if r.segment != last_segment:
            rows.append("")
            last_segment = r.segment
        sp = f"{r.speedup}x" if r.speedup is not None else "—"
        base = f"{r.baseline_us:.1f}" if r.baseline_us is not None else "N/A"
        rows.append(
            f"{r.segment.ljust(seg_w)}  {r.name.ljust(name_w)}  "
            f"{r.median_us:>9.1f}  {r.p95_us:>9.1f}  "
            f"{base:>11}  {sp:>9}"
        )
    return "\n".join(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iters", type=int, default=500)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out", help="write JSON report to this path")
    args = parser.parse_args(argv)

    results = run_all(args.iters)
    payload = {
        "iters": args.iters,
        "stages": [r.to_dict() for r in results],
        "segments": sorted({r.segment for r in results}),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(_format_table(results))
        winners = [r.speedup for r in results if r.speedup and r.speedup > 1]
        if winners:
            print(
                f"\n{len(winners)} of {len(results)} stages beat the baseline. "
                f"Median speedup (winners): {statistics.median(winners)}x."
            )

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(payload, indent=2), encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
