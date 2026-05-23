# ADR-0004: Performance budgets and regression warnings in CI

**Status:** Accepted.
**Date:** 2026-05-19.
**Owner:** @wesleysimplicio.
**Related:** GitHub issue #79.

## Context

We already have two benchmark runners that exercise hot paths without making
model API calls:

* `scripts/benchmark_startup_perf.py` — import cost, tool-definition
  assembly, plugin discovery, batch session writes.
* `scripts/benchmark_runtime_usage.py` — runtime construction, parallel
  guard, OpenRouter metadata cache, batched session append.

Both are useful, but they're run manually. Nothing in CI catches a 2x
slowdown landing in a PR; nothing produces a machine-readable artifact
that we can diff against last week.

Issue #79 asks for a small, stable benchmark subset wired into CI as
**non-blocking** regression warnings.  Goal: catch obvious regressions
fast, without making people fight flaky perf gates.

## Decision

We add:

1. `scripts/perf_budgets.json` — the budgets file.  One entry per tracked
   case with: `source` (benchmark script), `metric`, `budget` (seconds,
   median), and a one-line `description`.
2. `scripts/perf_budgets.py` — runner script.  Invokes the relevant
   benchmark in `--json` mode, parses the median for each tracked case,
   compares against the budget, and writes:
   - `perf-budgets-report.json` (machine-readable)
   - `perf-budgets-summary.md`  (human-readable table)
   Exit code is **always 0**.  This script is informational — never
   blocking.
3. `.github/workflows/perf-budgets.yml` — workflow with two triggers:
   - `workflow_dispatch` (manual)
   - `schedule` nightly at 07:00 UTC
   It runs the script, uploads both artifacts (30-day retention), and
   appends the markdown summary to the GitHub step summary.

### Tracked cases (initial set)

| case | runner | budget (s, median) |
| --- | --- | ---: |
| `import_model_tools` | `benchmark_startup_perf.py` | 2.5 |
| `get_tool_definitions` | `benchmark_startup_perf.py` | 1.5 |
| `session_append_messages_batch` | `benchmark_startup_perf.py` | 0.5 |
| `parallel_guard_read_files` | `benchmark_runtime_usage.py` | 0.5 |
| `openrouter_metadata_disk_cache` | `benchmark_runtime_usage.py` | 1.5 |

Budgets are intentionally generous — they're alarms for clear regressions,
not optimisation targets.  A ratio of `< 1.0x` is "ok"; a ratio of
`>= 1.0x` is flagged as `over_budget`.

### Hardware assumption

Budgets are calibrated for the default `ubuntu-latest` GitHub Actions
runner (2 vCPU, 7 GB RAM).  Local runs may produce different absolute
numbers — that's fine.  The script writes the medians it observed so a
maintainer can compare apples to apples.

## How to update budgets

1. Run the script locally on a clean checkout of the branch you want to
   anchor to:

   ```bash
   python scripts/perf_budgets.py --samples 5 --output /tmp/local.json
   ```

2. If a budget needs to change (true perf improvement, or a deliberate
   trade-off), edit `scripts/perf_budgets.json` and:
   - Keep the budget at least **1.5x** the median you actually observed,
     so that runner jitter doesn't flap the warning every other night.
   - Add a one-line note in the commit message saying *why* the budget
     changed (improvement, refactor accepted slowdown, etc.).
3. If a new hot path needs to be tracked, add a case to
   `perf_budgets.json` and make sure the corresponding benchmark runner
   knows the case name.

## Consequences

* CI nightly cost grows by ~one job run per day, ~5–10 minutes.
* PRs are not gated.  A regression that lands during the day shows up
  the next morning in the nightly report; we accept that latency in
  exchange for zero false-positive blocking.
* The JSON artifact format is `schema_version: 1`.  If we change it,
  bump and document the change in this ADR.

## Non-goals

* This is **not** a benchmark suite for marketing claims — see the
  existing `generate_hermes_turbo_benchmark_report.py` for that.
* This is **not** a performance gate.  Blocking gates need stable,
  reproducible numbers (dedicated runners, controlled noise).  We are
  not paying for that.
