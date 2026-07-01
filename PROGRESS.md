# Progress Log

## Cycle 2026-07-01 — hot-path performance pass (Simplicio scan)

Goal (operator): scan the repo with Simplicio and make performance
improvements.

Approach: `simplicio map` for orientation, then an adversarially-verified
8-dimension hot-path audit (find → refute) over the streaming, compression,
scrubber, state, and caching paths. 10 findings confirmed+recommended; applied
the safe subset, each grounded in code that was read and covered by tests.

Landed (version bump 0.15.2 → 0.15.3):

1. **`agent/prompt_caching.py`** — `apply_anthropic_cache_control` shallow-copies
   the message list and deep-copies only the ≤4 messages it marks, instead of
   `copy.deepcopy` of the whole transcript on every Anthropic send (per-message,
   scales with conversation size). +2 non-mutation regression tests.
2. **`agent/chat_completion_helpers.py` + `run_agent.py`** — dropped
   `len(repr(chunk/event))` per stream chunk (pydantic deep-repr every token) at
   4 sites for a cheap delta-length proxy on `_diag["bytes"]`.
3. **`agent/chat_completion_helpers.py`** — streamed tool-call arguments now
   accumulate in a list joined once (was `dict[...]["arguments"] += frag`, O(N²)).
4. **`agent/think_scrubber.py`** — precomputed lowercased tag tuples; removes
   per-delta `tag.lower()` across 5 hot-path scan helpers.
5. **`hermes_state.py`** — `get_messages_around` / `get_anchored_view` read
   `tool_calls` via `_json_loads` (fast-json aware) like the sibling readers.

Validation: **463 passed** across think_scrubber, prompt_caching, cache_boundary,
stream_drop_logging, anthropic_prompt_cache_policy, chat_completions transport,
hermes_state (+ anchored/around), streaming, and streaming_tool_call_repair.
(`tests/run_agent/test_partial_stream_finish_reason.py` has 3 failures that
**pre-date** this work — reproduced on clean HEAD via `git stash`.)

Note: the multi-agent audit fan-out left an unreviewed orjson migration in
`tools/*.py` + `gateway/run.py` + a new `tools/_fastjson.py`. That was **out of
scope, unvetted**, and reverted; the diff is saved in the session scratchpad as
`unreviewed-tools-orjson-migration.patch` if we want to review it deliberately
later.

Not committed/pushed (project rule: no push; left for operator review).

## Cycle 2026-06-05 — upstream review + operational + speed

Goal (operator): run the Hermes/Turbo update, see what changed, keep our
changes, verify whether upstream is faster than ours, and make the app
operational and faster.

What landed:

1. **Operational baseline.** Container shipped with **no deps installed** — CLI
   could not import (`No module named 'dotenv'`). Installed core runtime +
   `[fast]` extra (orjson/uvloop) + built the Rust wheel. `hermes --help`,
   `hermes report savings`, `hermes migrate-from-openclaw --benchmark` all run.
2. **Upstream review** (`docs/upstream-sync/2026-06-05-review.md`). Captured the
   50 newest upstream commits (HEAD `80672754`). **None are speed work** — all
   bug/stability fixes. Verdict: upstream is *not* faster than the Turbo stack.
   Recorded the baseline in `scripts/upstream-sync/sync-state.json`.
3. **Took the one good upstream fix:** WAL `TRUNCATE` checkpoint in
   `hermes_state.py` (upstream `46b2afc56`, #24034) — stops unbounded
   `state.db-wal` growth; matches the disk-GC guardrail. 234 state tests pass.
4. **Speed fix — Rust dispatch** (`agent/_hermes_fast.py`). Measured the Rust
   bridge as a *net loss* for estimation/truncation (FFI + JSON-serialize cost)
   and a ~3× win only for `parse_tool_call_delta`. Now routes accordingly;
   `HERMES_RUST_ESTIMATES=1` opts back in. +3 tests (7 pass).
5. **Perf-tooling bugs.** `benchmark_startup_perf.py` lacked `--case`, so
   `perf_budgets.py` always failed its 3 startup cases — fixed. `perf_budgets.py`
   now marks skipped runners as `skipped`, not false `error`s.
6. **Operational regression fixed.** A prior "keep only benchmark winners"
   cleanup deleted `token_savings`/`gain_analytics`/`stage_timer`/`dashboard`
   but left their shipped #136–#139 consumers + tests, hard-breaking
   `hermes report savings`. Restored all four (stdlib-only, `keep-turbo`).

Validation: final gate **320 passed, 2 skipped** across `_hermes_fast`,
telemetry, state/WAL, web_perf, migrate_openclaw, scripts. Perf budgets: 4/5
under budget; `parallel_guard_read_files` over by 1.29× (shared-CPU noise,
non-blocking).

## Current Status

Open issues #136–#139 are implemented on branch
`claude/project-issues-testing-9boGQ`. Tests added and green. Issue #140
is a strategic roadmap epic and is intentionally out of scope (parent issue
for the sub-issues we just closed). Earlier #81–#103 work documented below
is unchanged.

## Checkpoints

### Checkpoint 1 — Scoping
Status: done.
Audited the repo: `agent/telemetry/`, `scripts/`, `hermes_cli/web_server.py`,
`hermes_cli/claw.py` already provide the building blocks. Decided to add
narrowly-scoped modules + minimal wiring instead of larger refactors.

### Checkpoint 2 — Implementation
Status: done.
- `scripts/turbo_score.py` + `docs/turbo-score-baselines.json` + workflow
  `.github/workflows/daily-turbo-score.yml` (#136).
- `agent/telemetry/savings_report.py` + `hermes report savings` subparser in
  `hermes_cli/main.py` (#138).
- `hermes_cli/migrate_openclaw.py` + `hermes migrate-from-openclaw` subparser
  (#139). Delegates to existing `hermes claw migrate`; adds `--benchmark`
  flag that prints a Markdown comparison report.
- `hermes_cli/web_perf.py` + registration in `hermes_cli/web_server.py`
  adding `/perf` + `/api/perf/*` endpoints (#137).
- `hermes_cli/commands.py` registry entries for the new commands.
- `CHANGELOG.md` entry covering the four issues.

### Checkpoint 3 — Validation
Status: done.

| Command | Result | Notes |
|---|---|---|
| `pytest tests/scripts/test_turbo_score.py` | 10 passed | unit tests |
| `pytest tests/agent/telemetry/test_savings_report.py` | 13 passed | unit tests |
| `pytest tests/hermes_cli/test_migrate_from_openclaw.py` | 10 passed | unit tests |
| `pytest tests/hermes_cli/test_web_perf.py` | 11 passed | unit + TestClient |
| `pytest tests/token_saver tests/router tests/agent/telemetry tests/registry tests/contracts tests/agent/test_token_cache.py tests/agent/test_governor.py tests/test_ci_compact.py tests/test_github_compact.py tests/test_evidence_store.py tests/test_prompt_cache_stability.py tests/scripts` | 182 passed | full target set, no regressions |
| `pytest tests/hermes_cli/test_claw.py tests/hermes_cli/test_subparser_routing_fallback.py tests/hermes_cli/test_skills_subparser.py` | 49 passed | existing CLI suites unchanged |
| `python scripts/turbo_score.py` | 62.78 / 100 | live data |
| `python -m hermes_cli.main report savings --since 30d --json` | runs | 0 records on fresh env |
| `python -m hermes_cli.main migrate-from-openclaw --dry-run --benchmark --source /tmp/nonexistent` | runs | falls back to published baselines |
| `from hermes_cli.web_server import app; TestClient(app).get('/api/perf/turbo_score')` | 200 | live endpoint |
| `from hermes_cli.web_server import app; TestClient(app).get('/perf')` | 200 | live HTML view |

### Checkpoint 4 — Integration batch (P1-P7 + benchmark + daily sync)
Status: done.
Added:
- `agent/project_mapper/fingerprint.py` + tests (P1, 6 tests).
- `.hermes-meta.json` + `agent/meta_contract.py` + tests (P2, 9 tests).
- `prompts/runtime/hermes-turbo.md` + `hermes_cli/prompt_sync.py` + tests (P3, 8 tests).
- `agent/contracts/concise_response.py::TupleStatusEnvelope` + tests (P4, 6 tests).
- `.github/workflows/dod.yml` (P5).
- `hermes_cli/prompt_section.py` + tests (P6, 6 tests).
- `agent/telemetry/receipts.py` + tests (P7, 5 tests).
- `scripts/benchmark_turbo_vs_baseline.py` + `docs/perf/turbo-vs-baseline.md`
  + `docs/perf/turbo-vs-baseline-baseline.json`.
- `.github/workflows/upstream-sync-daily.yml` (cron 06:00 UTC).
- `.agents/AGENTS.yool.md` extended with new capability blocks.

Validation:
- `pytest <new+legacy>` -> **40 new + 170 legacy** all green.
- `tests/eval/compression_safety/runner.py` -> 5/5.
- `eval/clawbench/runner.py` -> 5/5.
- `scripts/benchmark_turbo_vs_baseline.py --iters 300` -> headline
  speedups: `project_mapper` **36.65x**, `router` **157.30x**.

## Blockers

None.

## Earlier History (issues #81-#103)

All 23 open issues (#81-#103) addressed in the prior cycle. Implementations
landed across merged PRs #106-#128 plus gap-fill commits on this branch.
See `GOAL_RESULT.md` for the full historical detail; tests still pass.
