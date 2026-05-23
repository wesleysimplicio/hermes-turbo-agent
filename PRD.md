# PRD - Open issues #136-#139 (May 22 2026 cycle)

## Objective

Close the four open feature issues on `wesleysimplicio/hermes-turbo-agent`:

- #136 Automate daily benchmark battle cards + Turbo Score
- #137 Turn runtime performance dashboard into an interactive web view
- #138 Weekly automated Token Savings Report
- #139 `hermes migrate-from-openclaw --benchmark` command

Issue #140 is a strategic roadmap epic and is out of scope for this PRD.

## Context

The repository already has:

- `scripts/generate_hermes_turbo_battle_cards.py` — static SVG battle cards
- `agent/telemetry/{token_savings, stage_timer, gain_analytics, dashboard}.py`
- `agent/telemetry/cache_usage.py` — Anthropic/OpenAI cache parsing
- `hermes_cli/claw.py` — existing OpenClaw migration
- `hermes_cli/web_server.py` — FastAPI dashboard at `127.0.0.1:9119`

What is missing per the issues:

- A unified **Turbo Score** computed from the existing benchmark data and a
  daily GH Actions workflow that refreshes it.
- A **web view** of the runtime telemetry (stage percentiles + token savings)
  surfaced through the existing dashboard.
- A **Token Savings Report** with weekly cadence, cost estimates, and
  `hermes report savings` CLI integration.
- A **`hermes migrate-from-openclaw --benchmark`** alias that runs the
  existing `claw migrate` flow and produces a side-by-side performance
  comparison after migration.

## Requirements

- [ ] `scripts/turbo_score.py` computes Turbo Score from existing benchmark JSON
- [ ] `.github/workflows/daily-turbo-score.yml` runs the score daily
- [ ] `/api/perf/*` endpoints + `/perf` HTML view in the web dashboard
- [ ] `agent/telemetry/savings_report.py` produces weekly savings reports
- [ ] `hermes report savings` CLI command
- [ ] `hermes migrate-from-openclaw [--benchmark]` CLI alias for `claw migrate`
- [ ] Targeted unit tests for each new module
- [ ] All new code is no-secret, no-external-dependency, stdlib-only where
      possible

## Non-Goals

- Rewriting the existing `claw migrate` flow
- Replacing the existing `hermes dashboard` web UI; only adding a new tab/view
- Building a real-time websocket telemetry stream (out of scope for this PRD)

## Validation Commands

```bash
python -m pytest tests/scripts/test_turbo_score.py \
                 tests/agent/telemetry/test_savings_report.py \
                 tests/hermes_cli/test_migrate_from_openclaw.py \
                 tests/hermes_cli/test_perf_dashboard.py -o addopts=""
python scripts/turbo_score.py --json
python -m agent.telemetry.savings_report --json
```

## Done When

- [ ] All four issues have associated implementations + tests
- [ ] PROGRESS.md updated
- [ ] GOAL_RESULT.md written
