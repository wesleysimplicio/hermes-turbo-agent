# Goal Result

## SkillOpt — self-evolving skill optimization (current task)

Implemented **SkillOpt** (https://microsoft.github.io/SkillOpt/) on branch
`claude/skillopt-implementation-6JVkM`: optimize a compact natural-language
*skill document* for a **frozen** agent (the skill text is the trainable state;
weights never change) via the loop **Rollout → Reflect → Edit → Gate**.

Fit for this repo: Hermes' headline feature is a closed learning loop where
"skills self-improve during use", so SkillOpt slots in as a first-class,
offline-reproducible optimizer over `SKILL.md` documents.

### What was built

- **`agent/skillopt/`** — the engine, stdlib-only, zero import side effects:
  - `types.py` — `Task`, `Trajectory`, `EditOp`, `EditBudget` (the *textual
    learning rate*), `ApplyResult`, `GateDecision`, `IterationLog`,
    `OptimizationResult`.
  - `document.py` — `SkillDocument` with bounded `add`/`delete`/`replace` edits;
    applying edits returns a new document so the gate can validate candidates.
  - `memory.py` — `RejectedEditBuffer` (negative feedback so punished
    directions aren't re-proposed) + `MetaSkillMemory` (optimizer-side extended
    feedback that never bloats the deployed skill).
  - `reflect.py` — `LocalReflector` (deterministic, mines graded-against terms
    missing from the skill) + `LLMReflector` (wraps any `complete(prompt)->str`,
    analyzes success/failure batches independently) + robust `parse_edit_ops`.
  - `rollout.py` — deterministic `OverlapRollout` proxy target +
    `complete_via_auxiliary` to wire Hermes' configured model.
  - `optimizer.py` — `SkillOptimizer`: the 4-stage loop, held-out validation
    gate, slow updates after validated win streaks, eval cache. Exports only
    `best_skill`.
- **CLI** — `hermes skillopt optimize <skill> --tasks <tasks.json>` in
  `hermes_cli/skillopt.py`, wired into `hermes_cli/main.py` (subparser +
  `_BUILTIN_SUBCOMMANDS`) and `hermes_cli/commands.py` (slash-command registry).
- **Docs/example** — `docs/skillopt.md`,
  `datagen-config-examples/skillopt_tasks.example.json`.
- **Tests** — `tests/agent/skillopt/{test_document,test_memory,test_reflect,test_optimizer,test_rollout}.py`
  and `tests/hermes_cli/test_skillopt.py`.

### Validation

| Command | Result |
|---|---|
| `pytest tests/agent/skillopt tests/hermes_cli/test_skillopt.py` | **51 passed** |
| `pytest tests/hermes_cli/test_commands.py tests/hermes_cli/test_kanban_cli.py` | **190 passed** (registry invariants hold) |
| `hermes skillopt optimize` (example task set) | bare skill **0.13 → 0.61**; gate rejects regressions; slow-update widening visible in the trace |

Pre-existing gateway/slack suite failures in this sandbox are missing
`pytest-asyncio`, unrelated to this change. No remote push performed.

---

## Summary

Closed all four open feature issues on `wesleysimplicio/hermes-turbo-agent`:

- **#136** — Automated Daily Benchmark Battle Cards + **Turbo Score**
- **#137** — Interactive **Web Performance Dashboard** view
- **#138** — Weekly automated **Token Savings Report**
- **#139** — `hermes migrate-from-openclaw --benchmark` command

Issue #140 is a strategic roadmap epic (parent issue), explicitly out of scope.
The earlier #81–#103 work documented in the previous GOAL_RESULT is unchanged.

## Changed Files (this cycle)

### New modules
- `scripts/turbo_score.py` — Turbo Score computation (latency, throughput,
  memory, cold-start, token-savings combined into a 0-100 figure of merit).
- `docs/turbo-score-baselines.json` — memory/cold-start baselines for
  Turbo Score families that the upstream benchmark JSON doesn't cover.
- `.github/workflows/daily-turbo-score.yml` — daily CI workflow that
  refreshes the score and uploads Markdown/JSON artifacts.
- `agent/telemetry/savings_report.py` — weekly token-savings report module
  with USD cost estimation (overridable price table per adapter).
- `hermes_cli/migrate_openclaw.py` — `hermes migrate-from-openclaw`
  command implementation (delegates to `hermes claw migrate`, adds
  `--benchmark` flag that prints a side-by-side Markdown comparison).
- `hermes_cli/web_perf.py` — `/perf` HTML view + `/api/perf/*` JSON
  endpoints for the existing FastAPI dashboard.

### Tests
- `tests/scripts/test_turbo_score.py` — 10 cases
- `tests/agent/telemetry/test_savings_report.py` — 13 cases
- `tests/hermes_cli/test_migrate_from_openclaw.py` — 10 cases
- `tests/hermes_cli/test_web_perf.py` — 11 cases (incl. live TestClient probes)

### Wiring (small edits)
- `hermes_cli/main.py` — registered `report` and `migrate-from-openclaw`
  subparsers; added the new commands to `_BUILTIN_SUBCOMMANDS`.
- `hermes_cli/commands.py` — added `CommandDef` entries for the two new
  top-level commands so they appear in autocomplete and `--help`.
- `hermes_cli/web_server.py` — added the three new `/api/perf/*` paths
  to `_PUBLIC_API_PATHS` and wired `web_perf.register()` after the
  existing routes (before the SPA catch-all).
- `CHANGELOG.md`, `PROGRESS.md`, `PRD.md`, `GOAL_RESULT.md` — updated.

## Validation Commands

```bash
python -m pytest \
  tests/scripts/test_turbo_score.py \
  tests/agent/telemetry/test_savings_report.py \
  tests/hermes_cli/test_migrate_from_openclaw.py \
  tests/hermes_cli/test_web_perf.py -o addopts=""

python -m pytest \
  tests/token_saver tests/router tests/agent/telemetry tests/registry \
  tests/contracts tests/agent/test_token_cache.py \
  tests/agent/test_governor.py tests/test_ci_compact.py \
  tests/test_github_compact.py tests/test_evidence_store.py \
  tests/test_prompt_cache_stability.py tests/scripts -o addopts=""

python scripts/turbo_score.py
python scripts/turbo_score.py --markdown
python -m hermes_cli.main report savings --since 30d --json
python -m hermes_cli.main migrate-from-openclaw --dry-run --benchmark \
  --source /tmp/nonexistent-openclaw
```

## Validation Results

- **New tests:** 44 passed (turbo_score 10, savings_report 13,
  migrate-from-openclaw 10, web_perf 11)
- **Wider regression set:** 182 passed across token_saver, router, telemetry,
  registry, contracts, governor, ci/github compact, evidence_store,
  prompt_cache_stability, scripts.
- **Existing CLI suites:** 49 passed across `test_claw.py`,
  `test_subparser_routing_fallback.py`, `test_skills_subparser.py`.
- **Live FastAPI probes:** `/api/perf/turbo_score` and `/perf` both return
  200 against the in-process app via `TestClient`.
- **Live Turbo Score** against shipped data: **62.78 / 100**
  (`latency` family pulls the score down due to two micro-benchmark
  regressions vs upstream; `throughput`, `memory`, `cold_start` all max out).

## Issue-by-Issue Acceptance

### #136 Daily Benchmark Battle Cards + Turbo Score
- [x] Daily-running benchmark workflow (`.github/workflows/daily-turbo-score.yml`)
- [x] Turbo Score calculated and exhibited (`scripts/turbo_score.py`)
- [x] Markdown output ready to embed in README "Why Turbo"

### #137 Performance Dashboard Web Interface
- [x] Accessible via the existing `hermes dashboard` (port 9119)
- [x] Backed by existing telemetry data (`stage_timer`, `token_savings`)
- [x] Comparison-friendly: groups by stage/provider/model/tool;
      provider-filterable in the future via the same API
- [x] No new heavy dependency — uses the existing FastAPI app and a static
      HTML page (no Streamlit/Gradio added)

### #138 Token Savings Report
- [x] Aggregates the JSONL ledger into a weekly report (`--since 7d` default)
- [x] Reports USD (price table per adapter, overridable via `--prices`)
- [x] Integrated with the token economy ledger
- [x] CLI: `hermes report savings`; library: `agent.telemetry.savings_report.build_report`
- [x] Markdown output suitable for email/Slack

### #139 Migration command with benchmark
- [x] `hermes migrate-from-openclaw [--benchmark]` working
- [x] Side-by-side report comparing OpenClaw baselines with live Hermes probes
- [x] Falls back to published baselines when OpenClaw is not present locally
- [x] Migration itself uses the existing safe-path in `hermes_cli/claw.py`

## Remaining Risks

- The OpenClaw baselines in `hermes_cli/migrate_openclaw.OPENCLAW_BASELINE`
  are static (sourced from the existing battle cards). Live probes for a
  user-installed OpenClaw could replace them on a follow-up.
- The Turbo Score family weights (`scripts/turbo_score.WEIGHTS`) are
  opinionated. A short README section calling them out would help users
  who recompute against different benchmark JSON.
- The `/perf` HTML page is dependency-free vanilla JS; if the project
  adopts a React shell for the dashboard later, the same `/api/perf/*`
  endpoints will keep working.

## Suggested PR Title

`feat: close issues #136-#139 — Turbo Score, web perf dashboard, savings report, migrate-from-openclaw`

## Suggested PR Body

```md
## Summary
- Adds the **Turbo Score** (`scripts/turbo_score.py`) + daily workflow (#136).
- Adds the **`/perf`** web view + `/api/perf/*` endpoints to the existing
  `hermes dashboard` (#137).
- Adds **`hermes report savings`** (#138) and the
  **`agent.telemetry.savings_report`** library backing it.
- Adds **`hermes migrate-from-openclaw --benchmark`** (#139).

## Validation
- [x] 44 new unit tests pass
- [x] 182 targeted regression tests still pass
- [x] 49 existing CLI tests still pass
- [x] Live FastAPI probes (`/api/perf/turbo_score`, `/perf`) return 200

## Risks
- Static OpenClaw baselines (vs probing a live install).
- Opinionated Turbo Score weights — documented in CHANGELOG + PRD.
```
