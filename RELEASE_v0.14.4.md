# Hermes Turbo Agent v0.14.4 — Turbo Score, Web Perf Dashboard, Savings Report, OpenClaw Migration

**Release date:** 2026-05-22.
**Previous version:** `0.14.3`.
**Issues closed:** `#136`, `#137`, `#138`, `#139`.
**Merged PR:** [#141](https://github.com/wesleysimplicio/hermes-turbo-agent/pull/141).

This release ships the four visibility-and-migration features tracked in
issues `#136`–`#139`. Together they turn the existing token-economy and
runtime-telemetry surfaces (delivered in `0.13.x`/`0.14.x`) into an
**operator-facing product** with a single score, a live web view, weekly
savings reports, and a guided OpenClaw migration path.

## Highlights

### 1. **Turbo Score** (`#136`)

A single 0–100 number that combines five families of measurements into one
comparable figure of merit:

| Family | Weight | Source |
|---|---:|---|
| Latency | 30 | `async_1000_task_ms`, `json_dumps_short_us`, `tool_call_parse_us` |
| Throughput | 20 | `token_estimate_batch_us` speedup |
| Memory | 15 | RSS baseline (`docs/turbo-score-baselines.json`) |
| Cold start | 15 | `cold_start_ms` |
| Token savings | 20 | telemetry `gain_analytics` overall_savings_pct |

The aggregator uses geometric-mean of speedup ratios so a single huge win
doesn't mask a regression. Families with missing inputs are dropped from
the total weight (and called out in the JSON output) instead of failing.

```bash
python scripts/turbo_score.py                # ASCII report
python scripts/turbo_score.py --json --out artifacts/score.json
python scripts/turbo_score.py --markdown      # README-ready
```

Live data on this branch: **62.78 / 100** (latency family pulled down by two
micro-benchmark regressions vs upstream; `throughput`, `memory`, `cold_start`
all maxed out).

### 2. **Web Performance Dashboard** (`#137`)

The existing `hermes dashboard` (FastAPI on `127.0.0.1:9119`) now serves an
interactive **/perf** view backed by three new JSON endpoints:

```
GET /api/perf/stage_summary?group_by=stage|provider|model|tool
GET /api/perf/token_savings?since=7d|24h|4w
GET /api/perf/turbo_score
GET /perf                          (vanilla-JS dashboard, polls every 15 s)
```

- Reads `~/.hermes/telemetry/*.jsonl` only — no network traffic.
- Public (no session-token) since dashboard binds to localhost.
- Zero new heavy dependencies; HTML+CSS+vanilla JS in one file.
- Plays nicely with the existing dashboard SPA — added before the SPA
  catch-all so `/perf` resolves first.

### 3. **Token Savings Report** (`#138`)

A weekly-style report on top of the existing `agent/telemetry/token_savings`
JSONL ledger. Adds:

- Time-window filtering: `--since 7d` (default), `24h`, `4w`, `30m`
- USD cost estimation with a small price table (`anthropic`, `openai`,
  `google`/`gemini`, `openrouter`, `default`) — overridable via
  `--prices path/to/prices.json`
- Per-adapter and per-tool breakdowns
- Markdown / JSON / plain-text output

CLI:

```bash
hermes report savings --since 7d                  # weekly default
hermes report savings --since 30d --markdown      # email/Slack-ready
hermes report savings --json --out report.json
```

Library entry point: `agent.telemetry.savings_report.build_report(records, since=…, prices=…)`.

### 4. **`hermes migrate-from-openclaw`** (`#139`)

A new top-level subcommand that delegates to the existing `hermes claw
migrate` flow and adds a `--benchmark` flag:

```bash
hermes migrate-from-openclaw --dry-run --benchmark
hermes migrate-from-openclaw --benchmark --benchmark-out reports/openclaw.md
```

After migration (or dry-run) the `--benchmark` step:

1. Probes the source OpenClaw directory for `VERSION` or `package.json`.
2. Runs a Hermes-side cold-start probe and reads token-savings %.
3. Pulls in the Turbo Score families.
4. Renders a side-by-side Markdown report — falls back to published
   OpenClaw baselines (`OPENCLAW_BASELINE`) when no local install exists.

Migration itself is unchanged: it reuses the audited `hermes_cli/claw.py`
flow, including pre-migration backups and the secrets-explicit-opt-in
posture.

## Daily Turbo Score workflow (`#136`)

`.github/workflows/daily-turbo-score.yml` runs every day at 07:00 UTC and:

- Computes the Turbo Score in three formats (text, JSON, Markdown).
- Best-effort regenerates the existing battle cards.
- Uploads both as build artifacts (90-day retention for the score,
  30-day for the cards).

## Validation

```bash
python -m pytest \
  tests/scripts/test_turbo_score.py \
  tests/agent/telemetry/test_savings_report.py \
  tests/hermes_cli/test_migrate_from_openclaw.py \
  tests/hermes_cli/test_web_perf.py -o addopts=""
# → 44 passed

python -m pytest \
  tests/token_saver tests/router tests/agent/telemetry tests/registry \
  tests/contracts tests/agent/test_token_cache.py tests/agent/test_governor.py \
  tests/test_ci_compact.py tests/test_github_compact.py \
  tests/test_evidence_store.py tests/test_prompt_cache_stability.py \
  tests/scripts \
  tests/hermes_cli/test_claw.py tests/hermes_cli/test_skills_subparser.py \
  tests/hermes_cli/test_migrate_from_openclaw.py tests/hermes_cli/test_web_perf.py \
  -o addopts="" -q
# → 252 passed
```

Smoke tests on a clean machine:

| Check | Result |
|---|---|
| `python scripts/turbo_score.py` | Score **62.78 / 100** |
| `python scripts/turbo_score.py --json` | round-trips through `json.loads` |
| `python -m hermes_cli.main report savings --since 7d --markdown` | renders empty report |
| `hermes report savings --log demo.jsonl --since 7d --markdown` (3 sample rows) | **165 000 tokens saved**, **$0.475 USD**, per-adapter table |
| `hermes migrate-from-openclaw --dry-run --benchmark --source /tmp/none` | renders full comparison with published baselines |
| `TestClient(app).get('/api/perf/turbo_score')` | `200` |
| `TestClient(app).get('/api/perf/stage_summary')` | `200` |
| `TestClient(app).get('/api/perf/token_savings?since=7d')` | `200` |
| `TestClient(app).get('/perf')` | `200`, returns interactive HTML |

## Files

**New modules:**
- `scripts/turbo_score.py`
- `docs/turbo-score-baselines.json`
- `.github/workflows/daily-turbo-score.yml`
- `agent/telemetry/savings_report.py`
- `hermes_cli/migrate_openclaw.py`
- `hermes_cli/web_perf.py`

**New tests** (44 cases):
- `tests/scripts/test_turbo_score.py` — 10 cases
- `tests/agent/telemetry/test_savings_report.py` — 13 cases
- `tests/hermes_cli/test_migrate_from_openclaw.py` — 10 cases
- `tests/hermes_cli/test_web_perf.py` — 11 cases (incl. live `TestClient` probes)

**Wiring (small edits):**
- `hermes_cli/main.py` — new `report` + `migrate-from-openclaw` subparsers and
  `_BUILTIN_SUBCOMMANDS` entries
- `hermes_cli/commands.py` — `CommandDef` autocomplete entries
- `hermes_cli/web_server.py` — `_PUBLIC_API_PATHS` extension + `register()` call

**Docs:**
- `CHANGELOG.md`, `PRD.md`, `PROGRESS.md`, `GOAL_RESULT.md`, this file

**Version bump:**
- `pyproject.toml` `0.14.2 → 0.14.4`
- `hermes_cli/__init__.py` `__version__` + `__release_date__`
- `acp_registry/agent.json`

## Compatibility & migration notes

- **No breaking changes.** All new commands and endpoints are additive.
- **No new heavy runtime dependencies.** FastAPI/uvicorn were already required
  by `hermes dashboard`; everything new is stdlib + the existing deps.
- **Telemetry log paths unchanged** (`~/.hermes/telemetry/*.jsonl`).
- The `hermes claw migrate` command still works exactly as before;
  `hermes migrate-from-openclaw` is an additive alias with the extra
  `--benchmark` flag.
- `_PUBLIC_API_PATHS` was extended with three perf endpoints. Read-only
  telemetry over a localhost-bound socket — same trust boundary as the
  rest of the dashboard.

## Suggested upgrade path

```bash
git pull
pip install -e ".[all,dev]"      # or your usual upgrade command
hermes report savings --since 7d # try the new report
hermes dashboard                 # open http://127.0.0.1:9119/perf
```

For OpenClaw users:

```bash
hermes migrate-from-openclaw --dry-run --benchmark
hermes migrate-from-openclaw --benchmark
```

## Acknowledgements

This release closes issues filed by `@wesleysimplicio`:

- `#136` — Daily Benchmark Battle Cards + Turbo Score
- `#137` — Performance Dashboard Web Interface
- `#138` — Token Savings Report
- `#139` — `hermes migrate-from-openclaw --benchmark`

Issue `#140` (strategic roadmap epic) remains open by design as the parent
tracker for the wider 2026 plan; the four sub-issues above were the
actionable items from that epic for this cycle.
