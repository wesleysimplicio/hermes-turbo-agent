# Benchmark Refresh After Upstream Sync

Keeps Hermes Turbo Agent performance claims grounded in measurement after every
upstream Hermes sync.

## Trigger

The `Benchmark Refresh` workflow (`.github/workflows/benchmark-refresh.yml`)
runs on:

- `workflow_dispatch` — manual run from the Actions tab.
- `push` to `sync/**`, `upstream-sync/**`, and `codex/hermes-turbo-hermes-daily-*`
  branches (the branch patterns used by upstream sync automation).

## What it does

1. Checks out the repository and installs the package plus benchmark/report
   dependencies (`reportlab`, `cairosvg`).
2. Runs `scripts/benchmarks/refresh.sh`, which invokes the existing Python
   benchmark runner (`scripts/refresh_sync_benchmarks.py`) and captures its
   output.
3. Writes a machine-readable JSON file per run to
   `benchmarks/results/<YYYY-MM-DD>.json` (UTC date). Fields:

   | Field    | Type   | Description                                  |
   | -------- | ------ | -------------------------------------------- |
   | `date`   | string | UTC date in `YYYY-MM-DD` format.             |
   | `commit` | string | Git SHA of the synced commit.                |
   | `ref`    | string | Branch ref the refresh ran against.          |
   | `status` | string | `ok` if benchmarks passed, `stale` on error. |
   | `runner` | string | Path to the runner script (provenance).      |
   | `log`    | string | Captured stdout/stderr of the runner.        |

4. Uploads the entire `benchmarks/results/` directory as the
   `benchmark-results` workflow artifact (90-day retention).

## Stale runs

If the benchmark runner is missing or exits non-zero, the JSON record carries
`"status": "stale"` and the workflow emits a `::warning::` annotation. Markdown,
PDF, and battle-card regeneration must consume only records with
`"status": "ok"`.

## Surfacing deltas in sync PRs

The upstream sync PR body should link to the most recent
`benchmarks/results/<date>.json` artifact and include the diff of measured
metrics versus the previous record. Stale records block the PR's performance
claim section until a clean refresh exists.
