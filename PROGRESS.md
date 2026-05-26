# Progress Log

## Current Status

SkillOpt (https://microsoft.github.io/SkillOpt/) implemented on branch
`claude/skillopt-implementation-6JVkM` (Checkpoint 5 below). 51 new tests
green; command-registry invariants hold. Earlier work unchanged:

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

### Checkpoint 5 — SkillOpt (https://microsoft.github.io/SkillOpt/)
Status: done. Branch `claude/skillopt-implementation-6JVkM`.

Implemented a faithful, dependency-light SkillOpt: optimize a natural-language
skill document for a frozen agent via Rollout → Reflect → Edit → Gate.

Added:
- `agent/skillopt/` package:
  - `types.py` — Task, Trajectory, EditOp, EditBudget (textual learning rate),
    ApplyResult, GateDecision, IterationLog, OptimizationResult.
  - `document.py` — `SkillDocument` with bounded add/delete/replace edits.
  - `memory.py` — `RejectedEditBuffer` (negative feedback) + `MetaSkillMemory`.
  - `reflect.py` — `LocalReflector` (deterministic) + `LLMReflector` (any
    `complete(prompt)->str`) + robust `parse_edit_ops`.
  - `rollout.py` — deterministic `OverlapRollout` proxy + `complete_via_auxiliary`.
  - `optimizer.py` — `SkillOptimizer`: the 4-stage loop, held-out gate, slow
    updates, eval cache. Exports only `best_skill`.
- `hermes_cli/skillopt.py` + `skillopt` subparser in `hermes_cli/main.py`
  (+ `_BUILTIN_SUBCOMMANDS`) + `CommandDef` in `hermes_cli/commands.py`.
- `docs/skillopt.md`, `datagen-config-examples/skillopt_tasks.example.json`.
- Tests: `tests/agent/skillopt/{test_document,test_memory,test_reflect,test_optimizer,test_rollout}.py`
  + `tests/hermes_cli/test_skillopt.py`.

Validation:
- `pytest tests/agent/skillopt tests/hermes_cli/test_skillopt.py` → **51 passed**.
- `pytest tests/hermes_cli/test_commands.py tests/hermes_cli/test_kanban_cli.py`
  → **190 passed** (command-registry invariants hold with the new entry).
- Full CLI dispatch verified: `hermes skillopt optimize <skill> --tasks <json>`
  improves a bare skill (e.g. 0.13 → 0.61 on the example task set), with the
  gate rejecting regressions and slow-update widening visible in the trace.
- Gateway/slack suite failures in this sandbox are pre-existing (missing
  `pytest-asyncio`), unrelated to this change.

## Blockers

None.

## Earlier History (issues #81-#103)

All 23 open issues (#81-#103) addressed in the prior cycle. Implementations
landed across merged PRs #106-#128 plus gap-fill commits on this branch.
See `GOAL_RESULT.md` for the full historical detail; tests still pass.
