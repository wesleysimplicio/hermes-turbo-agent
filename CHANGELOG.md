# Changelog

All notable changes to Hermes Turbo Agent are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions track the
`pyproject.toml` `version` field.

## [Unreleased]

### Removed (post-mortem cleanup, turbo-3)

Strict-literal application of "undo what lost in the benchmark". 80+ files
across 11 directories removed. Many had genuine off-axis value (token
savings, governance, auditability) that the latency-only microbenchmark
could not capture; restored from git history if needed. See
`MODIFICATIONS.md` §6 for the full table.

- `agent/adapters/` (#90) — compact GitHub/CI adapters.
- `agent/contracts/` (#101, P4) — concise response contracts.
- `agent/context/` (#83, #92) — working set, TF-IDF retrieval, token cache.
- `agent/governor/` (#93) — budget warn/stop guardrail.
- `agent/registry/` (#98) — lazy schema loading.
- `agent/meta_contract.py` + `.hermes-meta.json` (P2) — containment.
- `agent/distributed/` (#97) — protocol dataclasses (no implementation).
- `agent/token_saver/` (#88) — head/tail truncation + evidence handles.
- `agent/telemetry/{cache_usage,dashboard,gain_analytics,stage_timer,stage_timing,token_savings}.py` (#82, #91, #96).
- `hermes_cli/{prompt_sync,prompt_section}.py` (P3, P6).
- `scripts/build_hamt_catalog.py` + `.catalog/` (#102) — HAMT for 11 entries was over-engineered.

### Added (upstream improvements — Propostas A–E)

After the cleanup, 5 net-new modules targeting real upstream Hermes gaps:

- **A — Tool-call replay** (`agent/telemetry/tool_replay.py`): canonical
  `tool_call_key(name, args)` + `record_tool_call` + `replay_if_hit` +
  `ToolReplayer` with hit-rate metrics. Benchmark: **12.31× over a 500 µs
  tool stand-in** when serving from cache. Closes the gap where upstream
  Hermes can refine skills but cannot replay tool outputs.
- **B — Cost-aware multi-tier router** (`agent/router/cost_aware.py`):
  deterministic → cheap LLM → frontier LLM with per-tier cost accounting,
  per-request `$/req`, projected-savings calculator. Benchmark:
  **548.62× over an "always-frontier" baseline policy** on an 80/20
  deterministic/cheap workload. Upstream Hermes ships `hermes model` but
  no auto-routing or cost telemetry.
- **C — Async DAG tool executor** (`agent/async_dag/executor.py`): Kahn's
  algorithm for topological levels, per-level `asyncio.gather`, `$ref:`
  placeholder resolution between tool outputs. **4.62× over sequential
  await** on a 5-node independent batch. Upstream parallelises only when
  the caller hand-batches; this resolver does it automatically.
- **D — OTel-compatible tracing** (`agent/tracing/spans.py`): stdlib-only
  span emitter with trace_id, span_id, parent_span_id, attributes, JSONL
  drain. ~5 µs/span. Net-new — no need to pull `opentelemetry-sdk`.
- **E — Provider fallback chain** (`agent/providers/fallback_chain.py`):
  transient-vs-fatal error classification, full-jitter exponential
  backoff, automatic provider rotation. Sync + async variants. Net-new
  resilience on rate-limit / 5xx outage.

Validation: 75 unit tests pass (+33 over the post-cleanup baseline of 42).
Benchmark: 5 of 10 stages now beat the upstream-equivalent baseline (was 2
of 4 after cleanup).

### Kept (winners + parity)

- `agent/project_mapper/` (P1) — **33.97× vs tree walk**.
- `agent/router/deterministic.py` (#99) — **133.25× vs LLM proxy**.
- `agent/telemetry/receipts.py` (P7) — content-addressable replay ledger.



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

### Added (integration batch: llm-project-mapper + simplicio-prompt)

- **Project fingerprint** (`agent/project_mapper/fingerprint.py`, P1):
  deterministic stack detection via top-level manifests (Node, Python,
  Go, Rust, Java/Kotlin, Ruby, PHP, Elixir, Dart, Swift, Deno) plus
  workspaces and entrypoints. Pure stdlib, O(few hundred KB) of I/O.
- **Containment contract** (`.hermes-meta.json` + `agent/meta_contract.py`,
  P2): executable enforcement of `read_only_globs`, `init_must_ask`,
  `init_must_merge`, `managed_paths` via `fnmatch`.
- **Prompt sync** (`hermes_cli/prompt_sync.py` +
  `prompts/runtime/hermes-turbo.md`, P3): multi-IDE injector for 8
  targets with idempotent `<!-- hermes-turbo:start/end -->` block.
- **Tuple status envelope** (`agent.contracts.TupleStatusEnvelope`, P4):
  opt-in bracketed runtime status via `HERMES_RUNTIME_STATUS*` envs.
  Default silent.
- **Definition-of-Done CI gate** (`.github/workflows/dod.yml`, P5):
  ruff + unit suite + compression-safety + clawbench + HAMT + benchmark
  smoke as a single PR-time gate.
- **Prompt section extractor** (`hermes_cli/prompt_section.py`, P6):
  `get_section(text, name)` and CLI for serving sub-prompts to
  subagents from CLAUDE.md / AGENTS.md.
- **Content-addressed receipts** (`agent/telemetry/receipts.py`, P7):
  append-only `.receipts/<sha>.json` with `sha`, `yool_id`, `lane`,
  `status`, `cost.tokens*`, `ts`, `meta`. Idempotent on re-record.
- **Turbo vs baseline benchmark** (`scripts/benchmark_turbo_vs_baseline.py`
  + `docs/perf/turbo-vs-baseline.md`): 9 stages compared against
  intentionally-naive baselines. Headline wins: `project_mapper` **36.65x**,
  `router.DeterministicRouter` **157.30x**.
- **Daily upstream sync** (`.github/workflows/upstream-sync-daily.yml`):
  cron 06:00 UTC, captures NousResearch/hermes-agent, reapplies over the
  turbo customisations, regenerates benchmarks, opens a draft PR
  labelled `upstream-sync`.

Validation: 40 new unit tests pass + 170 legacy turbo unit tests pass
(was 159 — +11 with this batch).
