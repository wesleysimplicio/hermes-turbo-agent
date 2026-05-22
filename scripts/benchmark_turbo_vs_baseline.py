#!/usr/bin/env python3
"""Benchmark: Hermes Turbo (this fork) vs upstream-style baseline.

Measures the *runtime mechanisms* we added (#81-#103 + P1-P7), not LLM
quality. Each stage runs N iterations and reports tokens/ms/savings.

Stages:
    1. project_mapper.detect_fingerprint  (P1)
    2. meta_contract.check_write          (P2)
    3. concise_response (TerseAnswer)     (#101)
    4. tuple_status envelope render       (P4)
    5. deterministic router               (#99)
    6. token_saver proxy                  (#88)
    7. working_set hot/cold expand        (#92)
    8. receipts content-hash + lookup     (P7)
    9. lazy schema registry               (#98)

Run::

    python scripts/benchmark_turbo_vs_baseline.py          # full
    python scripts/benchmark_turbo_vs_baseline.py --smoke  # 1 iter (CI)
    python scripts/benchmark_turbo_vs_baseline.py --json   # JSON output
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
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


# ---- baselines: naive equivalents to compare against ----

def _baseline_fingerprint(root: Path) -> Dict[str, object]:
    # Naive: read the entire repo tree to "guess" stack — what an agent would
    # do without a fingerprinter.
    counters: Dict[str, int] = {}
    for path in root.rglob("*"):
        if path.is_file() and path.suffix:
            counters[path.suffix] = counters.get(path.suffix, 0) + 1
        if sum(counters.values()) > 5000:
            break
    return counters


def _baseline_check_write(path: str) -> bool:
    # Naive: regex over all rules in the .hermes-meta.json contract on every
    # check (no caching, no fnmatch table).
    import re
    rules = [
        r"\.git/.*", r".*\.lock", r"agent/.*", r"tests/.*",
        r"PRD\.md", r"CLAUDE\.md",
    ]
    return any(re.fullmatch(r, path) for r in rules)


def _baseline_terse_answer(text: str) -> str:
    # Naive: chop with no contract validation, no ellipsis budget.
    return text[:600]


def _baseline_router(text: str) -> str:
    # Naive: full LLM round-trip placeholder (10ms simulated).
    time.sleep(0.0001)  # 100us, not 10ms — keep benchmark fast
    return "llm-response"


def _baseline_token_saver(payload: str) -> str:
    # Naive: copy the whole payload (no truncation, no handle).
    return payload[:]


def _baseline_working_set(items: List[str], query: str) -> List[str]:
    return sorted(items, key=lambda s: -s.count(query))[:5]


def _baseline_receipt(payload: str) -> str:
    # Naive: md5 (no canonical storage, no append-only).
    import hashlib
    return hashlib.md5(payload.encode()).hexdigest()


def _baseline_lazy_schema(name: str) -> Dict[str, object]:
    # Naive: full schema dict built every call.
    return {"name": name, "type": "object", "properties": {"x": {"type": "string"}}}


# ---- turbo paths under test ----

def _bench_fingerprint(iters: int) -> StageResult:
    from agent.project_mapper import detect_fingerprint
    target = ROOT
    fp = detect_fingerprint(target)  # warm
    med, p95 = _time_us(lambda: detect_fingerprint(target), iters)
    base_med, _ = _time_us(lambda: _baseline_fingerprint(target), max(1, iters // 5))
    return StageResult(
        "project_mapper.detect_fingerprint", iters, med, p95,
        extra={"languages": float(len(fp.languages))},
        baseline_us=base_med,
    )


def _bench_meta_contract(iters: int) -> StageResult:
    from agent.meta_contract import check_write, load_meta
    meta = load_meta(ROOT)
    assert meta is not None, ".hermes-meta.json missing"
    target = ROOT / "agent" / "project_mapper" / "fingerprint.py"
    med, p95 = _time_us(lambda: check_write(meta, target), iters)
    base_med, _ = _time_us(
        lambda: _baseline_check_write("agent/project_mapper/fingerprint.py"),
        max(1, iters),
    )
    return StageResult(
        "meta_contract.check_write", iters, med, p95, baseline_us=base_med,
    )


def _bench_terse_answer(iters: int) -> StageResult:
    from agent.contracts import TerseAnswer
    long_text = "the quick brown fox " * 200
    med, p95 = _time_us(lambda: TerseAnswer(text=long_text), iters)
    base_med, _ = _time_us(lambda: _baseline_terse_answer(long_text), iters)
    return StageResult(
        "contracts.TerseAnswer", iters, med, p95, baseline_us=base_med,
    )


def _bench_tuple_envelope(iters: int) -> StageResult:
    os.environ.pop("HERMES_RUNTIME_STATUS", None)
    from agent.contracts import TupleStatusEnvelope
    env = TupleStatusEnvelope(
        snapshot="s", active="1", total="1", next_yool="y", partial="p",
    )
    med, p95 = _time_us(lambda: env.render(), iters)
    return StageResult(
        "contracts.TupleStatusEnvelope (silent)", iters, med, p95,
        extra={"emitted_bytes": 0.0},
    )


def _bench_router(iters: int) -> StageResult:
    try:
        from agent.router.deterministic import DeterministicRouter, RouteRule
    except ImportError:
        return StageResult("router.DeterministicRouter", 0, 0.0, 0.0)
    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex(
        "hello", r"^hi$", lambda _t, _m: "hello back",
    ))
    med, p95 = _time_us(lambda: router.route("hi"), iters)
    base_med, _ = _time_us(lambda: _baseline_router("hi"), max(1, iters // 10))
    return StageResult(
        "router.DeterministicRouter", iters, med, p95, baseline_us=base_med,
    )


def _bench_token_saver(iters: int) -> StageResult:
    try:
        from agent.token_saver.proxy import truncate_output
    except ImportError:
        return StageResult("token_saver.proxy.truncate_output", 0, 0.0, 0.0)
    import tempfile
    payload = "line\n" * 5000
    tmp = Path(tempfile.gettempdir()) / "hermes-bench-saver"
    med, p95 = _time_us(
        lambda: truncate_output(payload, max_lines=50, head=20, tail=20,
                                storage_dir=tmp),
        iters,
    )
    base_med, _ = _time_us(lambda: _baseline_token_saver(payload), iters)
    return StageResult(
        "token_saver.proxy.truncate_output", iters, med, p95, baseline_us=base_med,
    )


def _bench_working_set(iters: int) -> StageResult:
    try:
        from agent.context.retrieval import RelevanceScorer
    except ImportError:
        return StageResult("context.retrieval.RelevanceScorer", 0, 0.0, 0.0)
    corpus = {f"k{i}": f"alpha beta gamma item {i}" for i in range(50)}
    scorer = RelevanceScorer(corpus)
    med, p95 = _time_us(lambda: scorer.score("gamma item 7", top_k=5), iters)
    base_med, _ = _time_us(
        lambda: _baseline_working_set(list(corpus.values()), "gamma"), iters,
    )
    return StageResult(
        "context.retrieval.RelevanceScorer", iters, med, p95, baseline_us=base_med,
    )


def _bench_receipts(iters: int, tmp_dir: Path) -> StageResult:
    from agent.telemetry.receipts import content_hash, record_receipt
    payload = "rm -rf /tmp/nothing"
    record_receipt(payload=payload, tokens=10, directory=tmp_dir)
    med, p95 = _time_us(lambda: content_hash(payload), iters)
    base_med, _ = _time_us(lambda: _baseline_receipt(payload), iters)
    return StageResult(
        "telemetry.receipts.content_hash", iters, med, p95, baseline_us=base_med,
    )


def _bench_lazy_schema(iters: int) -> StageResult:
    try:
        from agent.registry.lazy_schema import LazyToolRegistry
    except ImportError:
        return StageResult("registry.lazy_schema.LazyToolRegistry", 0, 0.0, 0.0)
    registry = LazyToolRegistry()
    schema = {"name": "x", "type": "object"}
    registry.register("x", "desc", lambda: schema)
    med, p95 = _time_us(lambda: registry.load("x"), iters)  # cached path
    base_med, _ = _time_us(lambda: _baseline_lazy_schema("x"), iters)
    return StageResult(
        "registry.lazy_schema.LazyToolRegistry (cached)", iters, med, p95,
        baseline_us=base_med,
    )


def run_benchmarks(iters: int, tmp_dir: Path) -> List[StageResult]:
    return [
        _bench_fingerprint(iters),
        _bench_meta_contract(iters),
        _bench_terse_answer(iters),
        _bench_tuple_envelope(iters),
        _bench_router(iters),
        _bench_token_saver(iters),
        _bench_working_set(iters),
        _bench_receipts(iters, tmp_dir),
        _bench_lazy_schema(iters),
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
    rows.append("")
    rows.append(
        "note: baselines are intentionally naive (no validation, no disk, no\n"
        "      contract enforcement) — a speedup < 1x reflects the *cost of\n"
        "      correctness*, not a regression. Real wins live where Turbo\n"
        "      replaces an LLM call (router) or a full tree walk\n"
        "      (project_mapper)."
    )
    return "\n".join(rows)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes Turbo vs baseline benchmark.")
    parser.add_argument("--iters", type=int, default=500)
    parser.add_argument("--smoke", action="store_true",
                        help="CI smoke mode: 1 iter per stage")
    parser.add_argument("--json", action="store_true", help="emit JSON only")
    parser.add_argument("--out", help="write JSON report to this path")
    args = parser.parse_args(argv)

    iters = 1 if args.smoke else args.iters
    import tempfile
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
        avg_speedup = [r.speedup for r in results if r.speedup is not None]
        if avg_speedup:
            print(
                f"\nSummary: {len(avg_speedup)} stages with baseline, "
                f"median speedup {statistics.median(avg_speedup)}x"
            )

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(payload, indent=2), encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
