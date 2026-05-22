# Progress Log

## Current Status

All 23 open issues (#81-#103) addressed. Implementations land across the
prior merged PRs #106-#128 plus this branch's gap-fill commits.

## Checkpoints

### Checkpoint 1 — Audit
Status: done.
Result: confirmed substantive implementations exist for every issue in
`agent/`, `eval/`, `docs/`, `scripts/upstream-sync/`. Fixed one
`tmp_path` collision in `tests/token_saver/test_proxy.py`.

### Checkpoint 2 — Gap fills (this branch)
Status: done.
Added:
- `agent/token_saver/backend.py` + tests — RTK backend selector (#94).
- `agent/telemetry/stage_timing.py` + tests — runtime stage telemetry (#82).
- `agent/telemetry/cache_usage.py` + tests — Anthropic/OpenAI cache usage tracking (#96).
- `agent/context/token_cache.py` + tests — incremental token estimate cache (#83).
- `scripts/build_hamt_catalog.py` + `.catalog/` skeleton + tests — HAMT catalog builder (#102).
- `CHANGELOG.md` — first entry covering #81-#103.

### Checkpoint 3 — Validation
Status: done.
- `pytest tests/token_saver tests/router tests/agent/telemetry tests/registry tests/contracts tests/agent/test_token_cache.py tests/agent/test_governor.py tests/test_ci_compact.py tests/test_github_compact.py tests/test_evidence_store.py tests/test_prompt_cache_stability.py tests/scripts -o addopts=""` -> 159 passed.
- `python tests/eval/compression_safety/runner.py` -> 5/5 fixtures preserved.
- `python eval/clawbench/runner.py` -> 5/5 tasks scored 1.00.
- `python scripts/build_hamt_catalog.py --print-list` -> emits parsed yool ids.

## Blockers

None.

## Validation History

| Command | Result | Notes |
|---|---|---|
| `pytest <targeted suites>` | 159 passed | covers token_saver, router, telemetry, registry, contracts, token_cache, governor, ci/github compact, evidence_store, prompt_cache_stability, scripts |
| `tests/eval/compression_safety/runner.py` | 5/5 | golden fixtures preserved across compressor |
| `eval/clawbench/runner.py` | 5/5 | exact + soft scorers |
| `scripts/build_hamt_catalog.py --print-list` | ok | reads AGENTS.md yool blocks |
