# AGENTS.yool.md

Trimmed manifest after the post-mortem benchmark cleanup. Only capabilities
that beat or matched the upstream-equivalent baseline survived.

The full yool/tuple/HAMT spec adoption was reverted alongside the HAMT
catalog builder — at 11 capabilities, a flat dict outperforms HAMT.

---

### Hermes Runtime Dispatch

- yool_id: `agent.ops.runtime_dispatch`
- authority: ops
- lane: fast
- agent_terms:
    cpu_quota_pct: 70
    disk_quota_mb: 100
    timeout_s: 60
- description: Routes incoming task envelopes to the right worker lane and
  emits a receipt per dispatch.

### Hermes Shell Tool

- yool_id: `agent.ops.tool_shell`
- authority: ops
- lane: slow
- agent_terms:
    cpu_quota_pct: 50
    disk_quota_mb: 200
    timeout_s: 300
- description: Executes whitelisted shell commands on the host with cgroup
  enforcement. Disk quota covers temp scratch under `/tmp/hermes-shell`.

### Hermes LLM Call

- yool_id: `agent.ops.llm_call`
- authority: ops
- lane: slow
- agent_terms:
    cpu_quota_pct: 30
    disk_quota_mb: 50
    timeout_s: 180
- description: Forwards prompts to upstream model providers (DeepSeek,
  Anthropic, etc.) and records token/cost telemetry.

### Hermes Memory Manager

- yool_id: `agent.ops.memory_manager`
- authority: ops
- lane: background
- agent_terms:
    cpu_quota_pct: 40
    disk_quota_mb: 500
    timeout_s: 600
- description: Persists and compacts long-term memory artifacts under
  `.hermes_turbo/memories`. Higher disk quota to absorb consolidation passes.

### Hermes Code Review

- yool_id: `agent.review.code`
- authority: review
- lane: slow
- agent_terms:
    cpu_quota_pct: 50
    disk_quota_mb: 100
    timeout_s: 300
- description: Reads diffs and emits review comments. Read-only authority;
  never mutates the working tree.

### Hermes Project Mapper

- yool_id: `agent.dev.project_mapper`
- authority: dev
- lane: fast
- agent_terms:
    cpu_quota_pct: 30
    disk_quota_mb: 20
    timeout_s: 30
- description: Deterministic stack/workspace fingerprint via top-level
  manifests. **Benchmark winner: 36×–39× vs naïve tree walk.** See
  `agent/project_mapper/fingerprint.py`.

### Hermes Deterministic Router

- yool_id: `agent.ops.router_deterministic`
- authority: ops
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 10
    timeout_s: 5
- description: Regex-driven router that skips LLM round-trips on trivial
  intents. **Benchmark winner: 174×–185× vs LLM proxy.** See
  `agent/router/deterministic.py`.

### Hermes Tool Replay (Proposta A)

- yool_id: `agent.audit.tool_replay`
- authority: audit
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 500
    timeout_s: 10
- description: Deterministic tool-call replay via canonical
  `tool_call_key(name, args)` + `.receipts/tool/<sha>.json`. Benchmark
  winner: 12.31× vs a 500 µs tool stand-in on cache hit. See
  `agent/telemetry/tool_replay.py`.

### Hermes Cost-Aware Router (Proposta B)

- yool_id: `agent.ops.router_cost_aware`
- authority: ops
- lane: fast
- agent_terms:
    cpu_quota_pct: 25
    disk_quota_mb: 20
    timeout_s: 60
- description: Multi-tier router (deterministic → cheap → frontier) with
  per-request `$/req` accounting and projected-savings calculator.
  Benchmark winner: 548× vs always-frontier baseline. See
  `agent/router/cost_aware.py`.

### Hermes Async DAG (Proposta C)

- yool_id: `agent.ops.async_dag`
- authority: ops
- lane: fast
- agent_terms:
    cpu_quota_pct: 60
    disk_quota_mb: 50
    timeout_s: 300
- description: Topological-level executor for tool DAGs with `$ref:`
  resolution. Benchmark winner: 4.62× vs sequential await on 5
  independent nodes. See `agent/async_dag/executor.py`.

### Hermes Tracing (Proposta D)

- yool_id: `agent.audit.tracing`
- authority: audit
- lane: fast
- agent_terms:
    cpu_quota_pct: 10
    disk_quota_mb: 200
    timeout_s: 5
- description: Stdlib OTel-compatible span recorder. ~5 µs/span,
  JSONL drain. Replaces the bespoke telemetry deleted in the cleanup.
  See `agent/tracing/spans.py`.

### Hermes Provider Chain (Proposta E)

- yool_id: `agent.ops.provider_chain`
- authority: ops
- lane: slow
- agent_terms:
    cpu_quota_pct: 30
    disk_quota_mb: 20
    timeout_s: 120
- description: Provider fallback chain with transient/fatal classifier
  and full-jitter exponential backoff. Sync + async variants. See
  `agent/providers/fallback_chain.py`.

### Hermes Receipts

- yool_id: `agent.audit.receipts`
- authority: audit
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 200
    timeout_s: 15
- description: Append-only `.receipts/<sha>.json` content-addressable
  ledger. Hash-equal payloads short-circuit re-execution. Benchmark parity
  with md5 hash; the value is in cache hit rate on real workloads. See
  `agent/telemetry/receipts.py`.
