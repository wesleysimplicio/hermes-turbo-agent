# Hermes Turbo Runtime Prompt

> Canonical injectable block. Distributed via `hermes prompt sync` to
> `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
> `.codex/AGENTS.md`, `.cursorrules`, `.aider.conf.yml.md`, etc.
> Inspired by `wesleysimplicio/simplicio-prompt` (idempotent delimited blocks).

## Operating contract

- Read `PRD.md`, `PROGRESS.md`, `CLAUDE.md`, `AGENTS.md` before coding.
- Work in small checkpoints; validate the smallest relevant suite after each
  meaningful change; update `PROGRESS.md`.
- Stop only when work is complete, validation is documented in `GOAL_RESULT.md`,
  and the `[Unreleased]` entry of `CHANGELOG.md` reflects the change.

## Safe-speed path (before any LLM call)

1. Consult the receipts cache (`.receipts/<sha>.json`) — replay if hit.
2. Apply compression: token-saver proxy + working-set hot/cold + concise
   contracts (`TerseAnswer`, `ToolCall`, `Diagnostic`).
3. Route deterministically (`agent/router/deterministic.py`); only call the LLM
   on miss.
4. Respect the budget governor (warn at 70%, stop at 100%).
5. On rate-limit, use jittered backoff (`agent/retry_utils.py`) +
   `agent/nous_rate_guard.py`.

## Containment

The `.hermes-meta.json` contract is enforced by `agent.meta_contract`:

- `read_only_globs` → block (e.g. `*.lock`, `.git/**`, `.receipts/**`).
- `init_must_ask`   → ask before write (e.g. `PRD.md`, `Dockerfile`).
- `init_must_merge` → merge, never overwrite (e.g. `CLAUDE.md`).
- `managed_paths`   → allow (e.g. `agent/**`, `tests/**`).

## Response contract (bracketed, env-toggled)

When `HERMES_RUNTIME_STATUS=true` (default `false` — silent), respond with:

```
[Tuple Space Snapshot]
[Active Agents/Subagents]
[Total Agents/Subagents]
[Próximo Yool a executar]
[Resultado parcial]
```

Per-field toggles: `HERMES_RUNTIME_STATUS_SNAPSHOT`,
`HERMES_RUNTIME_STATUS_ACTIVE`, `HERMES_RUNTIME_STATUS_TOTAL`,
`HERMES_RUNTIME_STATUS_NEXT`, `HERMES_RUNTIME_STATUS_PARTIAL`.

## Capability addressing

Every registered agent in this repo declares a yool block in `AGENTS.md`:

```markdown
- yool_id: `agent.<authority>.<slug>`
- authority: dev | ops | review | audit
- lane: fast | slow | background
- agent_terms:
    cpu_quota_pct: 60       # MANDATORY (spec §11.1)
    disk_quota_mb: 100      # MANDATORY (spec §11.2)
    timeout_s: 300
```

HAMT catalog: rebuild with `python scripts/build_hamt_catalog.py`.
