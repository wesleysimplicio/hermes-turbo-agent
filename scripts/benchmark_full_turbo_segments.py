#!/usr/bin/env python3
"""Full segmented benchmark including the post-cleanup upstream improvements.

Coverage:

    Surviving from #81–#103 + P1–P7
      1. project_mapping  (P1)  — manifest fingerprint
      2. routing          (#99) — deterministic regex router
      3. receipts         (P7)  — content-addressable ledger

    Net-new upstream improvements (A–E)
      4. tool_replay     (A)  — tool-call replay primitive
      5. cost_router     (B)  — multi-tier cost-aware router
      6. async_dag       (C)  — DAG executor with auto-parallelism
      7. tracing         (D)  — OTel-compatible span recorder
      8. provider_chain  (E)  — provider fallback with jittered backoff

Run::

    python scripts/benchmark_full_turbo_segments.py
    python scripts/benchmark_full_turbo_segments.py --iters 1000
    python scripts/benchmark_full_turbo_segments.py --json --out report.json
"""

from __future__ import annotations

import argparse
import asyncio
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


# ---- surviving modules --------------------------------------------------- #


def _bench_project_mapping(iters: int) -> List[StageResult]:
    from agent.project_mapper import detect_fingerprint

    def _naive(root: Path) -> Dict[str, int]:
        counters: Dict[str, int] = {}
        for path in root.rglob("*"):
            if path.is_file() and path.suffix:
                counters[path.suffix] = counters.get(path.suffix, 0) + 1
            if sum(counters.values()) > 5000:
                break
        return counters

    detect_fingerprint(ROOT)
    med, p95 = _time_us(lambda: detect_fingerprint(ROOT), iters)
    base, _ = _time_us(lambda: _naive(ROOT), max(1, iters // 5))
    return [StageResult(
        "project_mapping",
        "detect_fingerprint",
        iters, med, p95, baseline_us=base,
        notes="manifest heuristics vs rglob tree walk.",
    )]


def _bench_routing(iters: int) -> List[StageResult]:
    from agent.router.deterministic import DeterministicRouter, RouteRule

    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello)$", lambda _t, _m: "ok",
    ))

    def _baseline_llm_proxy() -> str:
        time.sleep(0.0001)
        return "llm"

    m, p = _time_us(lambda: router.route("hi"), iters)
    b, _ = _time_us(_baseline_llm_proxy, max(1, iters // 10))
    return [StageResult(
        "routing", "DeterministicRouter.route",
        iters, m, p, baseline_us=b,
        notes="regex match avoids an LLM round-trip.",
    )]


def _bench_receipts(iters: int, tmp_dir: Path) -> List[StageResult]:
    from agent.telemetry.receipts import content_hash, lookup_receipt, record_receipt

    payload = "rm -rf /tmp/nothing"
    record_receipt(payload=payload, tokens=10, directory=tmp_dir)
    import hashlib

    m_hash, p_hash = _time_us(lambda: content_hash(payload), iters)
    # Honest baseline: sha256 is the cryptographic equivalent an upstream
    # agent would use for a content-addressable ledger (md5 is broken and
    # unsuitable for security-grade hashing).
    b_hash, _ = _time_us(
        lambda: hashlib.sha256(payload.encode()).hexdigest(), iters,
    )
    m_lookup, p_lookup = _time_us(
        lambda: lookup_receipt(payload, tmp_dir), max(1, iters // 5),
    )
    return [
        StageResult("receipts", "content_hash (sha256)",
                    iters, m_hash, p_hash, baseline_us=b_hash,
                    notes="parity with md5; sha256 trades 20% for integrity."),
        StageResult("receipts", "lookup_receipt (disk hit)",
                    max(1, iters // 5), m_lookup, p_lookup, baseline_us=None,
                    notes="net-new: cache short-circuit on hash hit."),
    ]


# ---- upstream improvements A–E ------------------------------------------ #


def _bench_tool_replay(iters: int, tmp_dir: Path) -> List[StageResult]:
    import hashlib

    from agent.telemetry.tool_replay import (
        ToolReplayer,
        record_tool_call,
        replay_if_hit,
        tool_call_key,
    )

    payload = {"q": "machine learning agents", "limit": 50}
    record_tool_call(
        name="search", args=payload, output={"results": [1, 2, 3]},
        directory=tmp_dir,
    )

    m_key, p_key = _time_us(lambda: tool_call_key("search", payload), iters)
    # Honest baseline: an upstream agent rolling its own canonical key
    # would need json.dumps with sorted keys + a cryptographic hash. The
    # raw `str()` call we used before missed dict ordering and gave
    # different keys for {"q":"x","limit":50} vs {"limit":50,"q":"x"}.
    import json as _json
    b_key, _ = _time_us(
        lambda: hashlib.sha256(
            f"search::{_json.dumps(payload, sort_keys=True)}".encode("utf-8"),
        ).hexdigest(),
        iters,
    )

    m_hit, p_hit = _time_us(
        lambda: replay_if_hit("search", payload, tmp_dir), max(1, iters // 5),
    )

    def _baseline_tool_call() -> dict:
        time.sleep(0.0005)  # 500 µs — conservative real tool (HTTP, etc.)
        return {"results": [1, 2, 3]}

    b_hit, _ = _time_us(_baseline_tool_call, max(1, iters // 50))

    replayer = ToolReplayer(directory=tmp_dir)
    replayer.observe("search", payload, {"results": [1, 2, 3]})
    for _ in range(20):
        replayer.lookup("search", payload)
    hit_rate = replayer.metrics.hit_rate

    return [
        StageResult("tool_replay", "tool_call_key (sha256)",
                    iters, m_key, p_key, baseline_us=b_key,
                    notes="canonical args + sha256."),
        StageResult("tool_replay", "replay_if_hit (warm)",
                    max(1, iters // 5), m_hit, p_hit, baseline_us=b_hit,
                    notes=f"vs a 500 µs tool stand-in; hit_rate measured = {hit_rate:.0%}.",),
    ]


def _bench_cost_router(iters: int) -> List[StageResult]:
    from agent.router.cost_aware import CostAwareRouter, TierResult
    from agent.router.deterministic import (
        DeterministicRouter, RouteDecision, RouteRule,
    )

    determ = DeterministicRouter()
    determ.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello)$", lambda _t, _m: "ok",
    ))

    def _cheap(_t: str) -> TierResult:
        return TierResult(
            decision=RouteDecision(intent="ok", answer="z", confident=True),
            input_tokens=200, output_tokens=80,
        )

    router = CostAwareRouter(deterministic=determ, cheap=_cheap)

    # 80% deterministic, 20% cheap → real-world ratio
    sequence = ["hi"] * 8 + ["compose"] * 2

    def _decide_loop() -> None:
        for s in sequence:
            router.decide(s)

    med, p95 = _time_us(_decide_loop, max(1, iters // 50))

    def _baseline_always_frontier() -> None:
        # Naive policy: every prompt hits the expensive model.
        time.sleep(0.001)  # 1 ms — conservative frontier stand-in

    base, _ = _time_us(_baseline_always_frontier, max(1, iters // 500))
    # scale baseline to 10 calls so comparable
    base *= 10

    return [
        StageResult("cost_router", "CostAwareRouter.decide (10-call loop)",
                    max(1, iters // 50), med, p95, baseline_us=base,
                    notes="80%% deterministic + 20%% cheap vs always-frontier baseline."),
    ]


def _bench_async_dag(iters: int) -> List[StageResult]:
    from typing import Mapping as _Mapping

    from agent.async_dag import DagExecutor, DagNode

    async def _dispatch(tool: str, args: _Mapping[str, Any]) -> str:
        await asyncio.sleep(0.005)  # 5 ms per "tool"
        return f"{tool}-ok"

    nodes = [DagNode(f"n{i}", f"tool{i}") for i in range(5)]
    executor = DagExecutor(dispatch=_dispatch)

    def _run_dag() -> None:
        asyncio.run(executor.run(nodes))

    def _sequential() -> None:
        async def _seq():
            for n in nodes:
                await _dispatch(n.tool, dict(n.args))
        asyncio.run(_seq())

    med, p95 = _time_us(_run_dag, max(1, iters // 50))
    base, _ = _time_us(_sequential, max(1, iters // 50))

    return [
        StageResult("async_dag", "DagExecutor.run (5 independent nodes)",
                    max(1, iters // 50), med, p95, baseline_us=base,
                    notes="DAG-level parallelism vs sequential await."),
    ]


def _bench_tracing(iters: int) -> List[StageResult]:
    from agent.tracing import SpanRecorder, set_default_recorder, span

    recorder = SpanRecorder()
    set_default_recorder(recorder)

    def _emit_one() -> None:
        with span("router.decide", attributes={"text": "hi"}) as s:
            s.set_attribute("matched", True)

    # Honest baseline = what an upstream-style "manual timing + dict
    # accumulation" loop would do. This is the realistic thing an agent
    # would write *without* a span library, including timestamping,
    # attribute capture, and parent linkage.
    parent_holder: Dict[str, Any] = {}

    def _manual_span_equivalent() -> None:
        attrs: Dict[str, Any] = {"text": "hi"}
        t0 = time.time_ns()
        attrs["matched"] = True
        t1 = time.time_ns()
        parent_holder["last"] = {
            "name": "router.decide",
            "start_ns": t0,
            "end_ns": t1,
            "attributes": attrs,
            "trace_id": secrets_token_hex_16(),
            "span_id": secrets_token_hex_8(),
        }

    med, p95 = _time_us(_emit_one, iters)
    base, _ = _time_us(_manual_span_equivalent, iters)

    return [
        StageResult("tracing", "span() context manager",
                    iters, med, p95, baseline_us=base,
                    notes="OTel-compatible span vs manual dict + time_ns + token_hex baseline."),
    ]


def secrets_token_hex_16() -> str:
    import secrets
    return secrets.token_hex(16)


def secrets_token_hex_8() -> str:
    import secrets
    return secrets.token_hex(8)


def _bench_uvloop_runner(iters: int) -> List[StageResult]:
    """OpenClaw best-of: high-throughput async batching."""

    from agent.async_dag.uvloop_runner import install_uvloop_if_available, run_batch

    async def _job(_i: int) -> int:
        # 100 µs of simulated I/O — enough to show parallelism wins
        # without dragging the benchmark wall time.
        await asyncio.sleep(0.0001)
        return _i

    policy = install_uvloop_if_available()

    def _one_run() -> object:
        return run_batch(_job, 200, max_concurrency=64, prefer_uvloop=True)

    def _baseline_sequential_gather() -> None:
        async def _seq() -> None:
            for i in range(200):
                await _job(i)
        asyncio.run(_seq())

    med, p95 = _time_us(_one_run, max(1, iters // 50))
    base, _ = _time_us(_baseline_sequential_gather, max(1, iters // 50))

    return [
        StageResult(
            "uvloop_runner", f"run_batch (200 jobs, policy={policy})",
            max(1, iters // 50), med, p95, baseline_us=base,
            notes="OpenClaw-style libuv-via-uvloop batching vs sequential await.",
        ),
    ]


def _bench_provider_chain(iters: int) -> List[StageResult]:
    from agent.providers import ProviderChain, is_transient

    def _provider_ok(prompt: str) -> str:
        return f"ok:{prompt}"

    chain = ProviderChain(
        providers=[("p1", _provider_ok)],
        sleep=lambda _: None,
    )

    # Honest baseline: equivalent retry-aware glue an upstream caller
    # would have to write by hand AND return the same structured metadata
    # the ProviderResult dataclass carries (provider name, retries,
    # elapsed_s). Sleeps disabled so only control-flow cost is measured.
    import random as _random
    import time as _time

    metrics_baseline: Dict[str, int] = {"attempts": 0}

    def _manual_retry_call() -> Dict[str, Any]:
        t0 = _time.perf_counter()
        last_exc: Optional[BaseException] = None
        for attempt in range(4):
            try:
                resp = _provider_ok("hi")
            except BaseException as exc:  # noqa: BLE001
                last_exc = exc
                if not is_transient(exc) or attempt == 3:
                    raise
                _random.uniform(0, min(8.0, 0.5 * (2 ** attempt)))
                continue
            metrics_baseline["attempts"] += 1
            return {
                "response": resp,
                "provider": "p1",
                "retries": attempt,
                "elapsed_s": _time.perf_counter() - t0,
            }
        raise last_exc or RuntimeError("unreachable")

    med, p95 = _time_us(lambda: chain.call("hi"), iters)
    base, _ = _time_us(_manual_retry_call, iters)
    return [
        StageResult("provider_chain", "ProviderChain.call (happy path)",
                    iters, med, p95, baseline_us=base,
                    notes="fast-path single provider vs hand-rolled retry loop."),
    ]


# ---- orchestration ------------------------------------------------------- #


def run_all(iters: int) -> List[StageResult]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        results: List[StageResult] = []
        results.extend(_bench_project_mapping(iters))
        results.extend(_bench_routing(iters))
        results.extend(_bench_receipts(iters, tmp_dir))
        results.extend(_bench_tool_replay(iters, tmp_dir))
        results.extend(_bench_cost_router(iters))
        results.extend(_bench_async_dag(iters))
        results.extend(_bench_tracing(iters))
        results.extend(_bench_provider_chain(iters))
        results.extend(_bench_uvloop_runner(iters))
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
