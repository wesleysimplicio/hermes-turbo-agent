#!/usr/bin/env python3
"""Benchmark: Hermes Turbo (this fork) vs upstream-style baseline.

Trimmed after the post-mortem cleanup. Only stages that beat or matched the
naïve upstream-equivalent baseline are still here:

    1. project_mapper.detect_fingerprint        (#P1)  vs tree walk
    2. router.DeterministicRouter.route         (#99)  vs LLM proxy
    3. telemetry.receipts.content_hash          (#P7)  vs md5

Run::

    python scripts/benchmark_turbo_vs_baseline.py          # 500 iters
    python scripts/benchmark_turbo_vs_baseline.py --smoke  # 1 iter, CI
    python scripts/benchmark_turbo_vs_baseline.py --json   # JSON output
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@dataclass
class StageResult:
    name: str
    iters: int
    median_us: float
    p95_us: float
    extra: Dict[str, float] = field(default_factory=dict)
    baseline_us: Optional[float] = None

    @property
    def speedup(self) -> Optional[float]:
        if self.baseline_us and self.median_us > 0:
            return round(self.baseline_us / self.median_us, 2)
        return None

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "iters": self.iters,
            "median_us": round(self.median_us, 1),
            "p95_us": round(self.p95_us, 1),
            "baseline_us": (
                round(self.baseline_us, 1) if self.baseline_us is not None else None
            ),
            "speedup_x": self.speedup,
            "extra": {k: round(v, 4) for k, v in self.extra.items()},
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


def _baseline_fingerprint(root: Path) -> Dict[str, int]:
    counters: Dict[str, int] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix:
            counters[path.suffix] = counters.get(path.suffix, 0) + 1
        if sum(counters.values()) > 5000:
            break
    return counters


def _baseline_llm_proxy() -> str:
    time.sleep(0.0001)
    return "llm-response"


def _bench_fingerprint(iters: int) -> StageResult:
    from agent.project_mapper import detect_fingerprint

    target = ROOT
    fp = detect_fingerprint(target)
    med, p95 = _time_us(lambda: detect_fingerprint(target), iters)
    base, _ = _time_us(lambda: _baseline_fingerprint(target), max(1, iters // 5))
    return StageResult(
        "project_mapper.detect_fingerprint", iters, med, p95,
        extra={"languages": float(len(fp.languages))},
        baseline_us=base,
    )


def _bench_router(iters: int) -> StageResult:
    from agent.router.deterministic import DeterministicRouter, RouteRule

    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello)$", lambda _t, _m: "hello back",
    ))
    med, p95 = _time_us(lambda: router.route("hi"), iters)
    base, _ = _time_us(_baseline_llm_proxy, max(1, iters // 10))
    return StageResult(
        "router.DeterministicRouter.route", iters, med, p95,
        baseline_us=base,
    )


def _bench_receipts(iters: int, tmp_dir: Path) -> StageResult:
    from agent.telemetry.receipts import content_hash, record_receipt

    payload = "rm -rf /tmp/nothing"
    record_receipt(payload=payload, tokens=10, directory=tmp_dir)
    med, p95 = _time_us(lambda: content_hash(payload), iters)
    import hashlib
    base, _ = _time_us(
        lambda: hashlib.md5(payload.encode()).hexdigest(), iters,
    )
    return StageResult(
        "telemetry.receipts.content_hash", iters, med, p95,
        baseline_us=base,
    )


def run_benchmarks(iters: int, tmp_dir: Path) -> List[StageResult]:
    return [
        _bench_fingerprint(iters),
        _bench_router(iters),
        _bench_receipts(iters, tmp_dir),
    ]


def _format_table(results: List[StageResult]) -> str:
    name_w = max(len(r.name) for r in results)
    rows = [
        f"{'stage'.ljust(name_w)}  {'iters':>6}  {'p50_us':>9}  {'p95_us':>9}  "
        f"{'baseline_us':>11}  {'speedup_x':>9}"
    ]
    rows.append("-" * len(rows[0]))
    for r in results:
        sp = f"{r.speedup}x" if r.speedup is not None else "—"
        base = f"{r.baseline_us:.1f}" if r.baseline_us is not None else "—"
        rows.append(
            f"{r.name.ljust(name_w)}  {r.iters:>6}  {r.median_us:>9.1f}  "
            f"{r.p95_us:>9.1f}  {base:>11}  {sp:>9}"
        )
    return "\n".join(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes Turbo vs baseline benchmark (lean).")
    parser.add_argument("--iters", type=int, default=500)
    parser.add_argument("--smoke", action="store_true",
                        help="CI smoke mode: 1 iter per stage")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--out", help="write JSON report to this path")
    args = parser.parse_args(argv)

    iters = 1 if args.smoke else args.iters
    with tempfile.TemporaryDirectory() as tmp:
        results = run_benchmarks(iters, Path(tmp))

    payload = {
        "iters": iters,
        "stages": [r.to_dict() for r in results],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(_format_table(results))

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(payload, indent=2), encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
