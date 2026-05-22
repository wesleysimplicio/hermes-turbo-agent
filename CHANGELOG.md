# Changelog

All notable changes to Hermes Turbo Agent are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions track the
`pyproject.toml` `version` field.

## [Unreleased]

### Added (token economy & runtime telemetry — issues #81-#103)

- **Token-saver proxy** (`agent/token_saver/proxy.py`, #88): head/tail truncation
  with file-backed expansion handles.
- **Token-saver backend selector** (`agent/token_saver/backend.py`, #94): chooses
  between native and `rtk` (https://github.com/rtk-ai/rtk) via the
  `HERMES_TOKEN_SAVER_BACKEND` env var (`native|rtk|auto`, default `auto`).
- **Evidence handles** (`tests/test_evidence_store.py`, #89): truncation
  materialises the full payload to disk; agents fetch by handle on demand.
- **GitHub/CI compact adapters** (`agent/adapters/`, #90): slim summaries of
  `gh issue|pr` JSON and grouped CI failures.
- **Token savings telemetry** (`agent/telemetry/token_savings.py`,
  `agent/telemetry/gain_analytics.py`, #91): JSONL ledger + aggregation CLI.
- **Cache usage tracking** (`agent/telemetry/cache_usage.py`, #96): parses
  Anthropic `cache_*_input_tokens` and OpenAI `cached_tokens`.
- **Stage timing** (`agent/telemetry/stage_timing.py`, #82): per-stage timers
  with provider/model/tool breakdowns and a stdout dashboard.
- **Context working set** (`agent/context/working_set.py`,
  `agent/context/retrieval.py`, #92): LRU hot set + cold-ref expansion driven
  by stdlib TF-IDF.
- **Incremental token cache** (`agent/context/token_cache.py`, #83): blake2b
  content keys, model-scoped invalidation, LRU eviction.
- **Budget governor** (`agent/governor/`, #93): token/cost/iteration budgets
  with warn-at-70% / stop-at-100% policy.
- **No-LLM router** (`agent/router/`, #99): deterministic rules + LLM fallback,
  counts avoided model calls.
- **Lazy schemas + skill metadata** (`agent/registry/lazy_schema.py`,
  `agent/registry/skill_meta.py`, #98): stub-only registration with on-demand
  expansion.
- **Concise response contracts** (`agent/contracts/concise_response.py`, #101):
  budget-capped `TerseAnswer` / `ToolCall` / `Diagnostic`.
- **Compression safety eval** (`tests/eval/compression_safety/`, #95): golden
  fixtures asserting preserved signal for failing tests, lint, type, CI,
  grep/diff inputs.
- **ClawBench-style harness** (`eval/clawbench/`, #100): JSON tasks scored
  exact/soft.
- **Distributed node host** (`agent/distributed/protocol.py`,
  `docs/adr/0006-distributed-node-host.md`, `docs/distributed/overview.md`,
  #97): dataclass wire protocol + ADR.
- **Warm daemon** (`hermes_cli/daemon.py`, `docs/runtime/warm-daemon.md`, #81):
  preloads tool registry, skill index, provider metadata.
- **Upstream sync system** (`scripts/upstream-sync/`,
  `.upstream-sync-policy.yml`, `scripts/validate_sync_policy.py`,
  `scripts/refresh_sync_benchmarks.py`, #85, #86, #87): capture, reapply,
  policy + validator, benchmark refresh.
- **HAMT catalog builder** (`scripts/build_hamt_catalog.py`, `.catalog/`,
  #102): parses AGENTS.md yool blocks, writes `.catalog/hamt.json` with
  branch-factor 32 / 30-bit blake2b hashes per yool-tuple-hamt v0.2.
- **RTK CLI skill** (`.skills/rtk-cli/SKILL.md`, #103): token-smart shell.
- **Sidecar evaluation** (`docs/perf/sidecar-benchmark-plan.md`, #84): ADR
  comparing pure-Python/uvloop, Node/libuv, Rust/Tokio.
- **Prompt-cache stable prefix** (`docs/adr/0005-prompt-cache-stable-prefix.md`,
  `tests/test_prompt_cache_stability.py`, #96).

### Documentation

- `docs/perf/`: `token-saver-proxy.md`, `token-savings-analytics.md`,
  `compact-adapters.md`, `concise-contracts.md`, `lazy-schemas.md`,
  `cache-boundary-tests.md`, `benchmark-refresh.md`, `sidecar-benchmark-plan.md`.
- `docs/runtime/`: `budget-governor.md`, `deterministic-router.md`,
  `warm-daemon.md`.
- `docs/upstream-sync/`: `playbook.md`, `policy.md`.

### Notes

This entry covers the token-economy and runtime-telemetry surface delivered
under issues #81–#103. Validation: 183 targeted unit tests pass
(`tests/token_saver`, `tests/router`, `tests/agent/telemetry`,
`tests/registry`, `tests/contracts`, `tests/agent/test_token_cache.py`,
`tests/agent/test_governor.py`, `tests/test_ci_compact.py`,
`tests/test_github_compact.py`, `tests/test_evidence_store.py`,
`tests/test_prompt_cache_stability.py`, `tests/scripts`,
`tests/eval/compression_safety/runner.py`, `eval/clawbench/runner.py`).
