# Turbo vs Baseline benchmark

Compares the runtime mechanisms added in the turbo fork (#81–#103 + P1–P7)
against intentionally-naive baselines (no validation, no contract, no
disk persistence). Run::

    python scripts/benchmark_turbo_vs_baseline.py            # 500 iters
    python scripts/benchmark_turbo_vs_baseline.py --smoke    # 1 iter, CI
    python scripts/benchmark_turbo_vs_baseline.py --json     # JSON only

The CI workflow `.github/workflows/dod.yml` invokes `--smoke` on every PR;
the daily upstream-sync workflow regenerates a full report and attaches it
to the sync PR as `docs/perf/turbo-vs-baseline-<run>.json`.

## Most recent baseline (300 iters, local dev container)

| stage | p50 (µs) | p95 (µs) | baseline (µs) | speedup |
|---|---:|---:|---:|---:|
| `project_mapper.detect_fingerprint` | 1811.9 | 1911.7 | 66 403.1 | **36.65x** |
| `router.DeterministicRouter` | 1.0 | 1.3 | 161.8 | **157.30x** |
| `telemetry.receipts.content_hash` | 0.6 | 0.7 | 0.7 | 1.12x |
| `meta_contract.check_write` | 41.3 | 60.2 | 1.9 | 0.05x ¹ |
| `contracts.TerseAnswer` | 0.9 | 1.3 | 0.2 | 0.18x ¹ |
| `contracts.TupleStatusEnvelope (silent)` | 4.1 | 7.1 | — | — |
| `token_saver.proxy.truncate_output` | 186.4 | 255.5 | 0.2 | 0.00x ¹ |
| `context.retrieval.RelevanceScorer` | 56.9 | 79.6 | 5.9 | 0.10x ¹ |
| `registry.lazy_schema.LazyToolRegistry (cached)` | 0.5 | 0.6 | 0.3 | 0.63x ¹ |

¹ Baseline does not enforce containment, contract, or disk persistence.
A "speedup < 1x" is the *cost of correctness* compared to a naive
implementation that ignores invariants the turbo path must preserve.

## What this benchmark measures

- **`project_mapper.detect_fingerprint`** vs a tree walk — 36× win because
  reading top-level manifests is bounded I/O while the naive walk is
  unbounded.
- **`router.DeterministicRouter`** vs a 100 µs LLM-call proxy — 157× win.
  Real LLM calls are 10⁴–10⁶× slower than this proxy, so the *real-world*
  ratio is orders of magnitude larger.
- **`telemetry.receipts.content_hash`** vs MD5 — parity at the hash level;
  the win lives at the *cache hit* level (record once, replay forever).

## What this benchmark does **not** measure

- LLM quality (covered by `eval/clawbench/`).
- End-to-end agent latency (covered by `scripts/benchmark_runtime_usage.py`).
- Token savings on real workloads (covered by
  `agent/telemetry/token_savings.py` JSONL ledger).

## Refresh cadence

- Every PR runs `--smoke` (1 iter, fail-fast).
- Daily upstream-sync runs full report and attaches the JSON to the PR.
- After an upstream sync (`scripts/upstream-sync/`), refresh with
  `scripts/refresh_sync_benchmarks.py`.
