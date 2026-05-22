# AGENTS.yool.md

Canonical manifest of agents registered in this repository under the
yool / tuple / HAMT capability-addressing scheme (spec v0.2).

Schema and rationale: [`docs/agents/yool-capability.md`](../docs/agents/yool-capability.md).
Decision record: [`.specs/architecture/ADR-001-yool-capability-addressing.md`](../.specs/architecture/ADR-001-yool-capability-addressing.md).

Guardrails (`cpu_quota_pct`, `disk_quota_mb`) are MANDATORY per spec §11.

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

### Hermes Context Builder

- yool_id: `agent.dev.context_builder`
- authority: dev
- lane: fast
- agent_terms:
    cpu_quota_pct: 60
    disk_quota_mb: 100
    timeout_s: 90
- description: Assembles prompt context from files, history, and skills.
  Bounded by disk_quota for the materialised context blob.

### Hermes Memory Manager

- yool_id: `agent.ops.memory_manager`
- authority: ops
- lane: background
- agent_terms:
    cpu_quota_pct: 40
    disk_quota_mb: 500
    timeout_s: 600
- description: Persists and compacts long-term memory artifacts under
  `.tota/memories`. Higher disk quota to absorb consolidation passes.

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
  manifests. Feeds the warm daemon and the no-LLM router. See
  `agent/project_mapper/fingerprint.py`.

### Hermes Meta Contract

- yool_id: `agent.audit.meta_contract`
- authority: audit
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 10
    timeout_s: 10
- description: Loads `.hermes-meta.json` and gates Write/Edit calls by
  `read_only_globs`, `init_must_ask`, `init_must_merge`, `managed_paths`.
  See `agent/meta_contract.py`.

### Hermes Prompt Sync

- yool_id: `agent.ops.prompt_sync`
- authority: ops
- lane: slow
- agent_terms:
    cpu_quota_pct: 30
    disk_quota_mb: 50
    timeout_s: 60
- description: Distributes `prompts/runtime/hermes-turbo.md` to 8 multi-IDE
  rule files via idempotent delimited blocks. See `hermes_cli/prompt_sync.py`.

### Hermes Prompt Section

- yool_id: `agent.dev.prompt_section`
- authority: dev
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 10
    timeout_s: 10
- description: Extracts a single markdown section so subagents receive
  only the relevant slice of CLAUDE.md/AGENTS.md. LRU 64. See
  `hermes_cli/prompt_section.py`.

### Hermes Receipts

- yool_id: `agent.audit.receipts`
- authority: audit
- lane: fast
- agent_terms:
    cpu_quota_pct: 20
    disk_quota_mb: 200
    timeout_s: 15
- description: Append-only `.receipts/<sha>.json` content-addressable
  ledger. Hash-equal payloads short-circuit re-execution. See
  `agent/telemetry/receipts.py`.
