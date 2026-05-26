# Changelog

All notable changes to Hermes Turbo Agent are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions track the
`pyproject.toml` `version` field.

## [Unreleased]

### Added (simplicio 6-layer task→code contract)

- **Vendored `simplicio` package** (`simplicio/`): the task-to-code 6-layer
  contract from [simplicio-cli](https://github.com/wesleysimplicio/simplicio-cli)
  v0.2.3 (mapper → precedent → skill-router → contract → test → verify),
  brought in-tree so the contract is available without a network install.
  `numpy`/`sentence-transformers` are lazy imports, so the package imports
  cleanly without the embedding stack and the no-precedent prompt path is
  dependency-free.
- **`simplicio` console script** and **`hermes simplicio …`** subcommand
  (`hermes_cli/simplicio_cmd.py`): forward `index|task|bench|smoke` verbatim
  to the vendored CLI. The embedding stack is lazy-installed on demand via the
  new `simplicio.embeddings` feature in `tools/lazy_deps.py`.
- Targeted unit tests under `tests/simplicio/` covering prompt stacking,
  provider config, skill routing, the content-hash embedding cache, and the
  `hermes simplicio` passthrough (26 tests, network-free).

### Fixed

- `hermes update` on Hermes Turbo fork installs now updates from the current
  origin tracking branch instead of assuming `origin/main`, then fetches and
  merges official Hermes (`upstream/main`) with fork changes preserved on top,
  including automatic fork-side resolution for remaining merge conflicts.
- Update checks now report fork-origin drift and official-upstream drift
  separately, avoiding false "behind origin/main" warnings on Hermes2.
- Git update guidance now preserves the `hermes2 update` command name for
  Hermes2 wrapper installs.
- Diverged origin history is no longer repaired with `reset --hard`; the
  updater leaves the local branch and any saved stash intact for manual review.

### Added (visibility & migration UX — issues #136-#139)

- **Turbo Score** (`scripts/turbo_score.py`, `docs/turbo-score-baselines.json`,
  #136): combines latency, throughput, memory, cold-start, and token-savings
  into a single 0-100 figure of merit. Emits text/JSON/Markdown.
- **Daily Turbo Score workflow** (`.github/workflows/daily-turbo-score.yml`,
  #136): refreshes the score on a 07:00 UTC schedule and publishes
  Markdown + JSON artifacts.
- **Web performance dashboard** (`hermes_cli/web_perf.py`, #137): adds
  `/perf` HTML view plus `/api/perf/{stage_summary,token_savings,turbo_score}`
  endpoints to the existing `hermes dashboard`. Lightweight, polls every 15s,
  reads from `~/.hermes/telemetry/*.jsonl`.
- **Token Savings Report** (`agent/telemetry/savings_report.py`, #138):
  weekly-style aggregation with cost estimates and per-adapter breakdowns.
  Exposed as `hermes report savings [--since 7d] [--markdown|--json]`.
- **`hermes migrate-from-openclaw`** (`hermes_cli/migrate_openclaw.py`,
  #139): thin alias around `hermes claw migrate` with a `--benchmark`
  flag that prints a side-by-side OpenClaw vs Turbo report.

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
