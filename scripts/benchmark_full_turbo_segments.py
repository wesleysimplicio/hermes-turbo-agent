#!/usr/bin/env python3
"""Full segmented benchmark: Hermes Turbo (this fork) vs upstream baseline.

Groups every customisation introduced under #81-#103 + P1-P7 into logical
segments and benchmarks each turbo path against a naïve baseline that
approximates the equivalent behaviour in upstream Hermes (which often has
no equivalent at all — those rows are marked ``baseline = N/A``).

Run::

    python scripts/benchmark_full_turbo_segments.py                # 500 iters
    python scripts/benchmark_full_turbo_segments.py --iters 1000   # heavy
    python scripts/benchmark_full_turbo_segments.py --json --out report.json

Segments::

    1. project_mapping   (P1)
    2. containment       (P2)
    3. multi_ide_prompt  (P3, P6)
    4. response_contract (#101, P4)
    5. token_saver       (#88)
    6. context           (#83, #92)
    7. routing           (#99, #93)
    8. telemetry         (#82, #91, #96, P7)
    9. registry          (#98)
   10. adapters          (#90)
   11. hamt              (#102)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# --------------------------------------------------------------------------- #
# Result containers                                                            #
# --------------------------------------------------------------------------- #


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


# --------------------------------------------------------------------------- #
# Segment 1 — project_mapping (P1)                                             #
# --------------------------------------------------------------------------- #


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

    detect_fingerprint(ROOT)  # warm
    med, p95 = _time_us(lambda: detect_fingerprint(ROOT), iters)
    base, _ = _time_us(lambda: _naive_tree_walk(ROOT), max(1, iters // 5))
    return [StageResult(
        "project_mapping", "detect_fingerprint (manifest heuristics)",
        iters, med, p95, baseline_us=base,
        notes="vs naïve rglob() tree walk that upstream would do.",
    )]


# --------------------------------------------------------------------------- #
# Segment 2 — containment (P2)                                                 #
# --------------------------------------------------------------------------- #


def _bench_containment(iters: int) -> List[StageResult]:
    from agent.meta_contract import check_write, load_meta
    import re

    meta = load_meta(ROOT)
    assert meta is not None, "missing .hermes-meta.json"
    target = ROOT / "agent" / "project_mapper" / "fingerprint.py"
    lock_target = ROOT / "uv.lock"

    def _baseline_regex_check(path: str) -> bool:
        rules = [r"\.git/.*", r".*\.lock", r"agent/.*",
                 r"tests/.*", r"PRD\.md", r"CLAUDE\.md"]
        return any(re.fullmatch(r, path) for r in rules)

    m, p = _time_us(lambda: check_write(meta, target), iters)
    b, _ = _time_us(lambda: _baseline_regex_check("agent/foo.py"), iters)
    block_m, block_p = _time_us(lambda: check_write(meta, lock_target), iters)

    return [
        StageResult(
            "containment", "check_write (managed allow path)",
            iters, m, p, baseline_us=b,
            notes="full rule resolution; baseline is regex-only.",
        ),
        StageResult(
            "containment", "check_write (read-only block path)",
            iters, block_m, block_p, baseline_us=None,
            notes="net-new: upstream has no read-only enforcement.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Segment 3 — multi_ide_prompt (P3, P6)                                        #
# --------------------------------------------------------------------------- #


def _bench_multi_ide_prompt(iters: int) -> List[StageResult]:
    from hermes_cli.prompt_section import get_section
    from hermes_cli.prompt_sync import _replace_or_append_block

    sample_doc = (ROOT / "prompts" / "runtime" / "hermes-turbo.md").read_text(
        encoding="utf-8",
    )
    existing = "preamble\n\n<!-- hermes-turbo:start -->\nold body\n<!-- hermes-turbo:end -->\n\npostamble\n"

    def _baseline_rewrite(existing: str, body: str) -> str:
        return body + "\n" + existing  # naive: prepend; never idempotent

    m1, p1 = _time_us(
        lambda: _replace_or_append_block(existing, sample_doc), iters,
    )
    b1, _ = _time_us(lambda: _baseline_rewrite(existing, sample_doc), iters)

    big_doc = (
        "# T\n\nintro\n\n## Operating contract\n\n" + ("x " * 1000)
        + "\n\n## Safe-speed path\n\nbody\n"
    )
    m2, p2 = _time_us(lambda: get_section(big_doc, "Operating contract"), iters)
    b2, _ = _time_us(lambda: big_doc.split("##")[1] if "##" in big_doc else "",
                     iters)

    return [
        StageResult(
            "multi_ide_prompt", "prompt_sync._replace_or_append_block (idempotent)",
            iters, m1, p1, baseline_us=b1,
            notes="idempotent in-place; baseline is naïve prepend.",
        ),
        StageResult(
            "multi_ide_prompt", "prompt_section.get_section",
            iters, m2, p2, baseline_us=b2,
            notes="header-bounded slice with case-insensitive match.",
        ),
    ]


# --------------------------------------------------------------------------- #
# Segment 4 — response_contract (#101, P4)                                     #
# --------------------------------------------------------------------------- #


def _bench_response_contract(iters: int) -> List[StageResult]:
    from agent.contracts import (
        Diagnostic,
        TerseAnswer,
        ToolCall,
        TupleStatusEnvelope,
    )

    long_text = "the quick brown fox " * 200
    m1, p1 = _time_us(lambda: TerseAnswer(text=long_text), iters)
    b1, _ = _time_us(lambda: long_text[:600], iters)

    m2, p2 = _time_us(
        lambda: ToolCall(name="search", args=[("q", "hello"), ("limit", "10")]),
        iters,
    )
    b2, _ = _time_us(lambda: {"name": "search", "args": []}, iters)

    m3, p3 = _time_us(
        lambda: Diagnostic(level="warning", code="X1", message="boom"), iters,
    )
    b3, _ = _time_us(lambda: ("warning", "X1", "boom"), iters)

    os.environ.pop("HERMES_RUNTIME_STATUS", None)
    env = TupleStatusEnvelope(snapshot="s", active="1", total="2",
                              next_yool="y", partial="p")
    m4, p4 = _time_us(lambda: env.render(), iters)

    return [
        StageResult("response_contract", "TerseAnswer", iters, m1, p1, b1,
                    notes="enforce_budget + ellipsis vs raw slice."),
        StageResult("response_contract", "ToolCall", iters, m2, p2, b2,
                    notes="full validation vs dict literal."),
        StageResult("response_contract", "Diagnostic", iters, m3, p3, b3,
                    notes="enum + budget vs tuple."),
        StageResult("response_contract",
                    "TupleStatusEnvelope.render (default silent)",
                    iters, m4, p4, None,
                    notes="zero output tokens by default; verbose via envs."),
    ]


# --------------------------------------------------------------------------- #
# Segment 5 — token_saver (#88)                                                #
# --------------------------------------------------------------------------- #


def _bench_token_saver(iters: int) -> List[StageResult]:
    from agent.token_saver.proxy import truncate_output

    tmp = Path(tempfile.gettempdir()) / "hermes-bench-saver"

    payloads = {
        "small (200 lines)": "line\n" * 200,
        "medium (5k lines)": "line\n" * 5_000,
        "large (50k lines)": "line\n" * 50_000,
    }
    out: List[StageResult] = []
    for label, payload in payloads.items():
        m, p = _time_us(
            lambda payload=payload: truncate_output(
                payload, max_lines=50, head=20, tail=20, storage_dir=tmp,
            ),
            iters,
        )
        b, _ = _time_us(lambda payload=payload: payload[:], iters)
        out.append(StageResult(
            "token_saver", f"truncate_output {label}",
            iters, m, p, baseline_us=b,
            notes="persists full payload + emits handle.",
        ))
    return out


# --------------------------------------------------------------------------- #
# Segment 6 — context (#83, #92)                                               #
# --------------------------------------------------------------------------- #


def _bench_context(iters: int) -> List[StageResult]:
    from agent.context.retrieval import RelevanceScorer
    from agent.context.token_cache import TokenEstimateCache
    from agent.context.working_set import WorkingSet

    corpus = {f"k{i}": f"alpha beta gamma item {i}" for i in range(50)}
    scorer = RelevanceScorer(corpus)
    m1, p1 = _time_us(lambda: scorer.score("gamma item 7", top_k=5), iters)
    b1, _ = _time_us(
        lambda: sorted(corpus.values(),
                       key=lambda s: -s.count("gamma"))[:5],
        iters,
    )

    cache = TokenEstimateCache(max_entries=1000)
    sample = "hello world " * 100
    cache.put(sample, 42, model="claude-opus-4-7")
    m2, p2 = _time_us(lambda: cache.get(sample, model="claude-opus-4-7"), iters)
    b2, _ = _time_us(lambda: len(sample) // 4, iters)

    ws = WorkingSet(token_budget=4000)
    ws.add("f1", "x" * 800, kind="snippet")
    ws.add("f2", "y" * 800, kind="snippet")
    m3, p3 = _time_us(lambda: ws.get("f1"), iters)
    b3, _ = _time_us(lambda: ("x" * 800)[:200], iters)

    return [
        StageResult("context", "retrieval.RelevanceScorer (TF-IDF)",
                    iters, m1, p1, b1,
                    notes="stdlib TF-IDF cosine vs sort-by-substring."),
        StageResult("context", "token_cache.get (LRU hit)",
                    iters, m2, p2, b2,
                    notes="blake2b LRU vs naïve len // 4."),
        StageResult("context", "working_set.get (hot fact)",
                    iters, m3, p3, b3,
                    notes="LRU hot set vs slice."),
    ]


# --------------------------------------------------------------------------- #
# Segment 7 — routing (#99, #93)                                               #
# --------------------------------------------------------------------------- #


def _bench_routing(iters: int) -> List[StageResult]:
    from agent.governor.budget import BudgetConfig, BudgetGovernor
    from agent.router.deterministic import DeterministicRouter, RouteRule

    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello|oi|olá)$", lambda _t, _m: "hello back",
    ))
    router.add_rule(RouteRule.from_regex(
        "time", r"^what (is|'s) the time\??$",
        lambda _t, _m: {"tool": "now", "args": {}},
    ))
    m1, p1 = _time_us(lambda: router.route("hi"), iters)

    def _baseline_llm_proxy() -> str:
        time.sleep(0.0001)  # 100 µs — conservative LLM stand-in
        return "llm-response"

    b1, _ = _time_us(_baseline_llm_proxy, max(1, iters // 10))

    cfg = BudgetConfig(max_tokens_per_loop=10_000_000_000,
                       max_cost_usd=1_000_000.0,
                       max_iterations=iters * 2)
    gov = BudgetGovernor(cfg)
    m2, p2 = _time_us(lambda: gov.record_step(tokens=10, cost_usd=0.0001), iters)
    b2, _ = _time_us(lambda: (10, 0.0001), iters)

    return [
        StageResult("routing", "DeterministicRouter.route",
                    iters, m1, p1, b1,
                    notes="regex match avoids an LLM round-trip entirely."),
        StageResult("routing", "BudgetGovernor.record_step",
                    iters, m2, p2, b2,
                    notes="warn-70%/stop-100% policy in pure Python."),
    ]


# --------------------------------------------------------------------------- #
# Segment 8 — telemetry (#82, #91, #96, P7)                                    #
# --------------------------------------------------------------------------- #


def _bench_telemetry(iters: int, tmp_dir: Path) -> List[StageResult]:
    from agent.telemetry.cache_usage import extract_anthropic_usage
    from agent.telemetry.receipts import content_hash, record_receipt
    from agent.telemetry.stage_timing import StageRecorder

    rec = StageRecorder()
    m1, p1 = _time_us(
        lambda: rec.record("planner", 12, provider="anthropic",
                           model="claude-opus-4-7"),
        iters,
    )
    b1, _ = _time_us(lambda: ("planner", 12), iters)

    payload = "rm -rf /tmp/nothing"
    record_receipt(payload=payload, tokens=10, directory=tmp_dir)
    m2, p2 = _time_us(lambda: content_hash(payload), iters)
    import hashlib
    b2, _ = _time_us(
        lambda: hashlib.md5(payload.encode()).hexdigest(), iters,
    )

    anthropic_resp = {
        "usage": {
            "input_tokens": 100,
            "output_tokens": 50,
            "cache_read_input_tokens": 200,
            "cache_creation_input_tokens": 30,
        },
    }
    m3, p3 = _time_us(lambda: extract_anthropic_usage(anthropic_resp), iters)
    b3, _ = _time_us(lambda: anthropic_resp["usage"]["input_tokens"], iters)

    return [
        StageResult("telemetry", "stage_timing.record",
                    iters, m1, p1, b1,
                    notes="per-stage timers with provider/model breakdown."),
        StageResult("telemetry", "receipts.content_hash (sha256)",
                    iters, m2, p2, b2,
                    notes="content-addressable; baseline is plain md5."),
        StageResult("telemetry", "cache_usage.extract_anthropic_usage",
                    iters, m3, p3, b3,
                    notes="parses cache_*_input_tokens fields."),
    ]


# --------------------------------------------------------------------------- #
# Segment 9 — registry (#98)                                                   #
# --------------------------------------------------------------------------- #


def _bench_registry(iters: int) -> List[StageResult]:
    from agent.registry.lazy_schema import LazyToolRegistry

    schema = {
        "name": "search",
        "type": "object",
        "properties": {"q": {"type": "string"}, "limit": {"type": "integer"}},
    }
    registry = LazyToolRegistry()
    registry.register("search", "search tool", lambda: schema)

    m1, p1 = _time_us(lambda: registry.load("search"), iters)  # cached
    b1, _ = _time_us(lambda: dict(schema), iters)

    def _cold_load() -> object:
        r = LazyToolRegistry()
        r.register("x", "x", lambda: schema)
        return r.load("x")

    m2, p2 = _time_us(_cold_load, iters)
    b2, _ = _time_us(lambda: dict(schema), iters)

    return [
        StageResult("registry", "LazyToolRegistry.load (cached)",
                    iters, m1, p1, b1,
                    notes="thread-safe LRU vs dict copy."),
        StageResult("registry", "LazyToolRegistry register + first load",
                    iters, m2, p2, b2,
                    notes="register + first schema build (cold path)."),
    ]


# --------------------------------------------------------------------------- #
# Segment 10 — adapters (#90)                                                  #
# --------------------------------------------------------------------------- #


def _bench_adapters(iters: int) -> List[StageResult]:
    from agent.adapters.ci_compact import parse_ci_log
    from agent.adapters.github_compact import compact_issue, compact_pr

    issue_raw = {
        "number": 123,
        "title": "fix the thing",
        "state": "open",
        "user": {"login": "wesley"},
        "body": "the body" * 100,
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "claude"}],
        "url": "https://example.com",
    }
    pr_raw = dict(issue_raw, additions=42, deletions=7, changed_files=3,
                  draft=True, base={"ref": "main"}, head={"ref": "feature"})
    ci_log = "\n".join([
        "2026-05-22T14:00:00Z some line",
        "FAILED tests/foo.py::test_a - AssertionError: boom",
        "PASSED tests/bar.py::test_b",
        "ERROR tests/baz.py::test_c - ImportError: missing dep",
    ] * 50)

    m1, p1 = _time_us(lambda: compact_issue(issue_raw), iters)
    b1, _ = _time_us(lambda: dict(issue_raw), iters)

    m2, p2 = _time_us(lambda: compact_pr(pr_raw), iters)
    b2, _ = _time_us(lambda: dict(pr_raw), iters)

    m3, p3 = _time_us(lambda: parse_ci_log(ci_log), iters)
    b3, _ = _time_us(lambda: ci_log.splitlines(), iters)

    return [
        StageResult("adapters", "github_compact.compact_issue",
                    iters, m1, p1, b1,
                    notes="slim summary + handle vs raw dict copy."),
        StageResult("adapters", "github_compact.compact_pr",
                    iters, m2, p2, b2,
                    notes="diff stats + base/head extraction."),
        StageResult("adapters", "ci_compact.parse_ci_log",
                    iters, m3, p3, b3,
                    notes="failure grouping + signatures."),
    ]


# --------------------------------------------------------------------------- #
# Segment 11 — HAMT (#102)                                                     #
# --------------------------------------------------------------------------- #


def _bench_hamt(iters: int) -> List[StageResult]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_hamt_catalog import build_catalog, hash30, lookup_catalog, parse_capabilities

    text = (ROOT / ".agents" / "AGENTS.yool.md").read_text(encoding="utf-8")

    m1, p1 = _time_us(lambda: parse_capabilities(text), iters)
    b1, _ = _time_us(lambda: text.splitlines(), iters)

    sample = "agent.dev.project_mapper"
    m2, p2 = _time_us(lambda: hash30(sample), iters)
    import hashlib
    b2, _ = _time_us(
        lambda: hashlib.sha256(sample.encode()).hexdigest()[:8], iters,
    )

    caps = parse_capabilities(text)
    catalog = build_catalog(caps)
    m3, p3 = _time_us(lambda: lookup_catalog(catalog, sample), iters)
    b3, _ = _time_us(lambda: any(c.get("yool_id") == sample for c in caps),
                     iters)

    return [
        StageResult("hamt", "build_hamt.parse_capabilities (AGENTS.yool.md)",
                    iters, m1, p1, b1,
                    notes="yool block parser vs raw splitlines."),
        StageResult("hamt", "build_hamt.hash30 (blake2b/30bit)",
                    iters, m2, p2, b2,
                    notes="HAMT-compatible content hash."),
        StageResult("hamt", "build_hamt.lookup_catalog",
                    iters, m3, p3, b3,
                    notes="HAMT lookup vs linear scan."),
    ]


# --------------------------------------------------------------------------- #
# Orchestration                                                                #
# --------------------------------------------------------------------------- #


def run_all(iters: int) -> List[StageResult]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        results: List[StageResult] = []
        results.extend(_bench_project_mapping(iters))
        results.extend(_bench_containment(iters))
        results.extend(_bench_multi_ide_prompt(iters))
        results.extend(_bench_response_contract(iters))
        results.extend(_bench_token_saver(iters))
        results.extend(_bench_context(iters))
        results.extend(_bench_routing(iters))
        results.extend(_bench_telemetry(iters, tmp_dir))
        results.extend(_bench_registry(iters))
        results.extend(_bench_adapters(iters))
        results.extend(_bench_hamt(iters))
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
    parser.add_argument("--json", action="store_true",
                        help="emit JSON only (no table)")
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
        ok_speedups = [r.speedup for r in results if r.speedup and r.speedup > 1]
        if ok_speedups:
            print(
                f"\n{len(ok_speedups)} of {len(results)} stages beat the baseline. "
                f"Median speedup (winning rows): {statistics.median(ok_speedups)}x."
            )

    if args.out:
        Path(args.out).expanduser().write_text(
            json.dumps(payload, indent=2), encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
