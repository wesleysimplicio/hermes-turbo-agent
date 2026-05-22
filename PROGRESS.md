# Progress Log

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

## Blockers

None.

## Earlier History (issues #81-#103)

All 23 open issues (#81-#103) addressed in the prior cycle. Implementations
landed across merged PRs #106-#128 plus gap-fill commits on this branch.
See `GOAL_RESULT.md` for the full historical detail; tests still pass.
