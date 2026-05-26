# Progress Log

## Current Status

Open issues #136–#139 are implemented on branch
`claude/project-issues-testing-9boGQ`. Tests added and green. Issue #140
is a strategic roadmap epic and is intentionally out of scope (parent issue
for the sub-issues we just closed). Earlier #81–#103 work documented below
is unchanged.

## Checkpoints

### Checkpoint 5 — `using-superpowers` skill (branch `claude/superpowers-skill-VJddB`)
Status: done.
Added the core obra/superpowers entry-point skill
`skills/software-development/using-superpowers/SKILL.md` (adapted to the Hermes
agent: `skill_view`/`delegate_task`, repo instruction priority). It establishes
"check for an applicable skill before any response/action" and ties together the
already-adapted `writing-plans`, `subagent-driven-development`,
`systematic-debugging`, `test-driven-development`, `requesting-code-review`
skills. The other superpowers skills (brainstorming, executing-plans,
dispatching-parallel-agents, receiving-code-review, using-git-worktrees,
finishing-a-development-branch, verification-before-completion, writing-skills)
remain unported and out of scope for this change.

Validation (all green):
- `tools.skill_manager_tool._validate_frontmatter` / `_validate_content_size` → OK (desc 99 chars).
- `website/scripts/generate-skill-docs.py::mdx_escape_body` runs clean (no box-drawing chars, no ascii-guard wrap needed).
- `pytest tests/website/test_generate_skill_docs.py tests/tools/test_skill_manager_tool.py` → **93 passed**.

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
