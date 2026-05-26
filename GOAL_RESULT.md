# Goal Result

## Latest cycle — vendor the simplicio 6-layer contract (branch `claude/simplicio-cli-setup-cOdQx`)

### Task

> Implement [simplicio-cli](https://github.com/wesleysimplicio/simplicio-cli)
> in this repo — mandatory whenever coding this CLI.

### Outcome — DONE

The standalone `simplicio-cli` (the task→code 6-layer contract: mapper →
precedent → skill-router → contract → test → verify) is now vendored in-tree
and reachable both as a standalone `simplicio` command and as `hermes
simplicio …`.

**New / changed files**

- `simplicio/` — vendored package from the PyPI sdist v0.2.3 (MIT):
  `__init__.py`, `cli.py`, `providers.py`, `prompt.py`, `pipeline.py`,
  `bench.py`, `precedent.py`, `skill_router.py`, `cache.py`,
  `templates/simplicio_prompt.md`. `numpy`/`sentence-transformers` are lazy
  imports so the tree imports without the embedding stack; vendored `open()`
  calls carry `encoding="utf-8"` for the ruff PLW1514 + windows-footguns gates.
- `hermes_cli/simplicio_cmd.py` — `hermes simplicio` passthrough; lazy-ensures
  the embedding stack for `index|task|bench` and forwards args verbatim.
- `hermes_cli/main.py` — `simplicio` subparser (`argparse.REMAINDER`) +
  `_BUILTIN_SUBCOMMANDS` entry.
- `hermes_cli/commands.py` — `simplicio` CommandDef.
- `tools/lazy_deps.py` — `simplicio.embeddings` lazy-install feature
  (`sentence-transformers>=2.2`, `numpy>=1.23`).
- `pyproject.toml` — `simplicio` console script, `packages.find` include,
  `templates/*.md` package-data. No dependency-resolution change, so
  `uv lock --check` is unaffected.
- `tests/simplicio/` — 26 network-free unit tests.

**Validation** (pytest 9.0.3 + numpy 2.4.6 in an ephemeral uv venv; the host
container ships neither the ML stack nor pytest):

- `pytest tests/simplicio/ -o addopts=""` → **26 passed**.
- `ruff check simplicio/ hermes_cli/simplicio_cmd.py` → clean.
- `python scripts/check-windows-footguns.py --all` → 0 footguns / 576 files.
- `python -m simplicio.cli --help` lists `index|task|bench|smoke`;
  `hermes simplicio smoke` exits 1 with provider info when no key is set.

**Usage**

```bash
hermes simplicio smoke                         # verify provider config
hermes simplicio index --stack angular         # cache repo precedent
hermes simplicio task "hide Delete for non-admins" \
  --stack angular --target src/app/x.component.html \
  --criteria "- admin: present\n- non-admin: absent" \
  --constraints "- build passes"
# or the standalone console script:
simplicio task "..." --target ...
```

Configure a provider via `SIMPLICIO_MODEL` + `SIMPLICIO_API_KEY`
(+ optional `SIMPLICIO_BASE_URL` for any OpenAI-compatible endpoint).

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
