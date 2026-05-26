# Turbo vs Baseline benchmark (post-mortem lean edition)

After the post-mortem cleanup, this report keeps only the modules that beat
or matched the upstream-equivalent baseline in the original 28-stage run.
Everything that lost in microbenchmark latency (with or without genuine
out-of-band value like token savings or governance) was removed from the
fork — the user explicitly chose this strict interpretation.

Run::

    python scripts/benchmark_turbo_vs_baseline.py            # 500 iters
    python scripts/benchmark_turbo_vs_baseline.py --smoke    # 1 iter, CI
    python scripts/benchmark_turbo_vs_baseline.py --json     # JSON only

## Lean result (3 stages, 500 iters)

| stage | p50 (µs) | p95 (µs) | baseline (µs) | speedup |
|---|---:|---:|---:|---:|
| `router.DeterministicRouter.route` | 1.4 | … | 191.9 | **133.25×** |
| `project_mapper.detect_fingerprint` | 2810.6 | … | 95479.9 | **33.97×** |
| `telemetry.receipts.content_hash` | 0.9 | … | 0.7 | 0.79× ¹ |

¹ sha256 vs md5 — slower than md5 by design (security/integrity), kept because
the value is in the cache-hit rate via `lookup_receipt`, not raw hash speed.

## Survivors

Three modules + one net-new helper:

- **`agent/router/deterministic.py`** — regex router skips LLM calls on
  trivial intents. Pays back the entire fork in the first ~10 saved LLM
  round-trips per session.
- **`agent/project_mapper/fingerprint.py`** — top-level manifest parser
  returns a `ProjectFingerprint`. Replaces "agent walks the tree to guess
  the stack" with a 1–3 ms read.
- **`agent/telemetry/receipts.py`** — append-only `.receipts/<sha>.json`
  ledger and `lookup_receipt` short-circuit replay.

## What was removed (and why)

See `MODIFICATIONS.md` §6 for the full removal manifest. Headline:

- 11 directories / 80+ files removed including: token saver, context working
  set, governor, lazy schema registry, response contracts, multi-IDE prompt
  sync, prompt section, GitHub/CI compact adapters, HAMT catalog,
  meta-contract, distributed protocol, telemetry stage/cache parsers.
- All of these lost in the original turbo-vs-baseline microbenchmark.
- Many had genuine value on **other** axes (output token savings, safety,
  auditability) that the latency-only benchmark missed. The user accepted
  that trade-off when picking the literal interpretation.

## Refresh cadence

- Every PR runs `--smoke` (1 iter, fail-fast) via `.github/workflows/dod.yml`.
- Daily upstream-sync (`.github/workflows/upstream-sync-daily.yml`) re-runs
  the full benchmark and attaches a fresh PDF + JSON to the sync PR.
