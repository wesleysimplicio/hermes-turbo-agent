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
