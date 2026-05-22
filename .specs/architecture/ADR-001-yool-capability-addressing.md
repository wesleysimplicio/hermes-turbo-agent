# ADR-001: Adopt yool / tuple / HAMT capability addressing

- Status: Accepted
- Date: 2026-05-21
- Refs: Issue #102, spec https://github.com/wesleysimplicio/yool-tuple-hamt (v0.2)

## Context

Hermes Turbo Agent exposes dozens of callable behaviors (runtime dispatch, shell
tools, LLM calls, context builders) across multiple authorities and lanes. Today
there is no canonical way to address those capabilities:

- Agents are referenced by ad hoc strings scattered across `agent/`, `acp_adapter/`,
  and `gateway/`.
- There is no shared opcode that downstream tooling (catalog, audit log,
  multi-agent router) can rely on to identify a call.
- Resource guardrails (CPU, disk, timeout) are described informally per agent,
  which has produced incidents where a runaway tool starved the host.

Reference implementations already shipped in adjacent repos (`llm-project-mapper`,
`SendSprint`) demonstrate that the yool/tuple/HAMT scheme is workable and cheap to
adopt incrementally.

## Decision

Adopt the yool / tuple / HAMT capability-addressing spec, v0.2, as the canonical
identification surface for every agent registered in this repository.

Every agent declaration MUST include:

- `yool_id`: stable opcode of the form `agent.<authority>.<slug>`
- `authority`: one of `dev | ops | review | audit`
- `lane`: one of `fast | slow | background`
- `agent_terms.cpu_quota_pct`: MANDATORY per spec §11.1
- `agent_terms.disk_quota_mb`: MANDATORY per spec §11.2
- `agent_terms.timeout_s`: timeout budget in seconds

The canonical registry lives in `docs/agents/yool-capability.md`. Individual agent
manifests are listed in `.agents/AGENTS.yool.md`. Both are markdown; machine-built
HAMT artifacts (`.catalog/hamt.json`, receipts) remain build outputs and are not
checked in (tracked separately under issue #102's catalog-builder scope).

## Consequences

Positive:

- Stable opcodes unlock catalog lookup, audit replay, and cross-repo routing.
- Mandatory guardrails make runaway tools a contract violation, not a surprise.
- Markdown-first adoption keeps the diff small and reviewable; tooling can land
  later without retro-fitting identifiers.

Negative / trade-offs:

- Every new agent costs a manifest line. Mitigated by the template in
  `.agents/AGENTS.yool.md`.
- Until the catalog builder lands, lookup is grep-based. Acceptable for now;
  flagged as follow-up.

## Alternatives considered

1. **Free-form strings**: status quo. Rejected — no contract, no audit surface.
2. **UUIDs per agent**: stable but opaque. Rejected — humans need to grep
   `agent.dev.shell`, not `f47ac10b-...`.
3. **Wait for upstream `yool-tuple-hamt` v1.0**: rejected — v0.2 already covers the
   addressing + guardrail surface we need. Upgrades are additive per spec §13.
