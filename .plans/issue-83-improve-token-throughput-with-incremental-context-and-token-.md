# Issue #83: Improve token throughput with incremental context and token cache

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/83

## Original description (excerpt)

```
## Goal
Attack one of the benchmark rows where OpenClaw still wins by making token/context accounting incremental.

## Context
The current benchmark shows Hermes Turbo Agent is strong overall but OpenClaw still wins token throughput. The next improvement should avoid re-estimating unchanged message and context segments.

## Acceptance criteria
- Cache token estimates by stable message/content hash.
- Add incremental context budget calculation for append-only conversation growth.
- Invalidate safely when model, tokenizer assumptions, or content changes.
- Add tests for cache correctness and stale-cache avoidance.
- Add a focused benchmark comparing cached vs uncached token budget paths.
```

## Implementation plan
- [ ] Read context (module / spec / ADR)
- [ ] Draft minimal change set
- [ ] Add tests (unit + e2e where applicable)
- [ ] Lint / typecheck / coverage >= 80% on diff
- [ ] Update CHANGELOG + docs
- [ ] Link ADR if architectural

## Definition of Done
Per AGENTS.md DoD: lint + unit + e2e green, evidence attached, AC checked, conventional commit.
