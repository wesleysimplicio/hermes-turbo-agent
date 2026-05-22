# Yool Capability Registry

Canonical registry of agent capabilities addressed under the
yool / tuple / HAMT scheme (spec v0.2,
https://github.com/wesleysimplicio/yool-tuple-hamt). See
[`.specs/architecture/ADR-001-yool-capability-addressing.md`](../../.specs/architecture/ADR-001-yool-capability-addressing.md)
for the why; see [`.agents/AGENTS.yool.md`](../../.agents/AGENTS.yool.md)
for the concrete agent manifests shipped in this repo.

## Required fields

Every agent registered in this repository MUST declare:

| Field                       | Type             | Notes                                                 |
| --------------------------- | ---------------- | ----------------------------------------------------- |
| `yool_id`                   | string           | `agent.<authority>.<slug>` (lowercase, dot-separated) |
| `authority`                 | enum             | `dev` \| `ops` \| `review` \| `audit`                 |
| `lane`                      | enum             | `fast` \| `slow` \| `background`                      |
| `agent_terms.cpu_quota_pct` | int 1..100       | MANDATORY guardrail (spec §11.1)                      |
| `agent_terms.disk_quota_mb` | int >= 1         | MANDATORY guardrail (spec §11.2)                      |
| `agent_terms.timeout_s`     | int >= 1         | execution budget in seconds                           |

`cpu_quota_pct` and `disk_quota_mb` are MANDATORY per Victor Genaro's review:
*"precisa de guardrail pra não fritar o processador. Você precisa de garbage
collector também pra não encher 100% do disco."* See spec §11.

## Authority semantics

- **dev**: writes code, runs builds, edits files in the working tree.
- **ops**: dispatches runtime work, manages processes, talks to the host.
- **review**: reads diffs and emits opinions; never mutates state.
- **audit**: reads logs and receipts; emits compliance signal only.

## Lane semantics

- **fast**: synchronous, < 5 s p95, on the user's request path.
- **slow**: synchronous-ish, multi-second tool calls (LLM, network).
- **background**: detached, queued; results materialised via receipt.

## Default guardrails

Unless an agent's manifest explicitly overrides, use:

```yaml
agent_terms:
  cpu_quota_pct: 60
  disk_quota_mb: 100
  timeout_s: 300
```

## Declaration template

Copy this block into `.agents/AGENTS.yool.md` (or the agent's own manifest) and
fill in:

```markdown
### <Human-readable name>

- yool_id: `agent.<authority>.<slug>`
- authority: dev | ops | review | audit
- lane: fast | slow | background
- agent_terms:
    cpu_quota_pct: 60
    disk_quota_mb: 100
    timeout_s: 300
- description: <one line, what this agent does>
```

## Naming rules

- `yool_id` is lowercase ASCII, dot-separated, no spaces.
- The middle segment matches `authority`.
- The final segment is a short verb-or-noun slug (`shell`, `dispatch`,
  `llm_call`). Hyphens disallowed inside a segment; use underscores.
- Once published, a `yool_id` is immutable. Renames go through a new ADR.

## Build-time artifacts

The HAMT catalog (`.catalog/hamt.json`) and receipt log (`.catalog/receipts/`)
are produced by the catalog builder (separate follow-up under issue #102). They
are gitignored and not checked in. This document plus
`.agents/AGENTS.yool.md` are the source of truth read by the builder.
