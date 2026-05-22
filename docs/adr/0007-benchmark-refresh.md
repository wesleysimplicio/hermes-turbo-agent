# ADR-0007: Benchmark refresh plan

**Status:** Proposed (Sprint 2 / issue #38).
**Date:** 2026-05-18.
**Owner:** TBD (dedicated benchmark run).

## Context

`tota_agent_benchmark_report.pdf` was generated against Tota 0.13.x.
After the upstream Hermes v0.14.0 merge into main (commit
`ab61ec254`) and the post-merge perf wave landings, the numbers in
the PDF no longer reflect the live performance surface.  We need a
side-by-side refresh against Hermes 0.14.0 stock so the "modified,
faster Hermes" claim stays defensible.

## What needs running

The benchmark script lives at
`scripts/generate_tota_benchmark_report.py` (~544 LOC).  It generates
the PDF from numbers fed in via the matching data files under
`docs/assets/tota-benchmark/`.  Those data files need refresh.

Benchmark surface (per `docs/tota-benchmark-win-plan.md`):

| Row | Workload | Tota target |
| --- | --- | --- |
| Cold start | Time-to-first-prompt for `tota` vs stock `hermes` | within 1.5× upstream |
| `browser_console` | 1000 evaluations p99 | match upstream's 180× post-merge |
| JSON dumps short | Internal hot-path bytes encode | ≤V8 |
| Tool-call parse | Rust direct-to-Python conversion | ≥3× stdlib |
| Token estimate | `estimate_messages_tokens` batch | ≥2× single-call loop |
| Async 1000-task | uvloop scheduler | ≥1.5× stdlib asyncio |
| Integration breadth | Gateway platforms enabled | report current surface |

## Runtime requirements

- Tota local install with `[fast]` + `[perf]` extras + Rust extension
  built (`scripts/install-rust.sh`).
- Hermes 0.14.0 stock install in a sibling venv for side-by-side.
- Node.js + Playwright for the browser_console benchmark.
- One Linux runner with at least 4 cores; macOS optional for the
  async-task tier.

## Output

- Updated `tota_agent_benchmark_report.pdf` committed to repo root.
- Refreshed assets under `docs/assets/tota-benchmark/generated/`.
- README's "Performance" section refreshed.
- Tota vs Hermes vs OpenClaw comparison rows in the PDF intro updated.

## Acceptance criteria

- Tota wins ≥5 of 7 rows.
- For any row Tota loses, document the gap and the closing strategy.
- The PDF is reproducible via
  `python scripts/generate_tota_benchmark_report.py` from the
  refreshed data files (no manual chart editing).

## Why this is open

The benchmark requires a real runtime environment that's hard to
script inside Claude Code's sandbox (Playwright, Rust toolchain, two
sibling venvs, 4-core minimum).  The work itself is tractable — it's
running benchmarks and committing the resulting PDF.  When an
operator has access to such a runner, they can pick this up in a
half-day.

## References

- `scripts/generate_tota_benchmark_report.py` (the generator).
- `docs/tota-benchmark-win-plan.md` (the per-row plan).
- `tota_agent_benchmark_report.pdf` (the current report).
- Issue #38.
