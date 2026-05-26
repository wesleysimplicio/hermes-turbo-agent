# Progress Log

## Current Status

On branch `claude/simplicio-cli-setup-cOdQx`: vendored the simplicio 6-layer
task→code contract into `simplicio/` and wired it into the CLI (`hermes
simplicio` + `simplicio` console script). See Checkpoint 5. Tests green.

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

### Checkpoint 5 — Vendor simplicio 6-layer contract
Status: done. Branch `claude/simplicio-cli-setup-cOdQx`.

Task: "Implement simplicio-cli (https://github.com/wesleysimplicio/simplicio-cli)
in this repo — mandatory whenever coding this CLI."

Done:
- Vendored the upstream package (PyPI sdist v0.2.3, MIT) into `simplicio/`:
  `__init__, cli, providers, prompt, pipeline, bench, precedent,
  skill_router, cache` + `templates/simplicio_prompt.md`.
- Adaptation for the host repo's dependency hygiene: `numpy` /
  `sentence-transformers` are imported lazily inside the functions that need
  them, so the module tree imports without the embedding stack and the
  no-precedent prompt path is dependency-free. Behaviour is identical once the
  stack is installed. Added `encoding="utf-8"` to the vendored `open()` calls
  to satisfy the ruff PLW1514 + windows-footguns blocking gates.
- Wiring: `simplicio` console script + `hermes simplicio …` passthrough
  (`hermes_cli/simplicio_cmd.py`, argparse REMAINDER), registered in
  `hermes_cli/main.py` (subparser + `_BUILTIN_SUBCOMMANDS`) and
  `hermes_cli/commands.py` (CommandDef). Embedding deps registered as the
  lazy-install feature `simplicio.embeddings` in `tools/lazy_deps.py`.
  `pyproject.toml`: script + `packages.find` include + `templates/*.md`
  package-data. No `[project.optional-dependencies]` change, so `uv lock
  --check` is unaffected.
- Tests: `tests/simplicio/` (prompt, providers, skill_router, cache,
  passthrough).

Validation (pytest 9.0.3 + numpy 2.4.6 in an ephemeral uv venv; host env has
no ML stack):

| Command | Result |
|---|---|
| `pytest tests/simplicio/ -o addopts=""` | 26 passed |
| `ruff check simplicio/ hermes_cli/simplicio_cmd.py` | All checks passed |
| `python scripts/check-windows-footguns.py --all` | 0 footguns (576 files) |
| `python -m py_compile` (edited host files) | OK |
| `python -m simplicio.cli --help` | lists index/task/bench/smoke |
| `hermes simplicio smoke` (no key) | exits 1 with provider info |

## Blockers

None. (Host container lacks the ML stack + pytest; validated in an ephemeral
uv venv. `hermes simplicio` lazy-installs `simplicio.embeddings` at first use.)

## Earlier History (issues #81-#103)

All 23 open issues (#81-#103) addressed in the prior cycle. Implementations
landed across merged PRs #106-#128 plus gap-fill commits on this branch.
See `GOAL_RESULT.md` for the full historical detail; tests still pass.
