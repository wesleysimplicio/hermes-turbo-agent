# Issue #93: Add token budget governor for autonomous loops

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/93

## Original description (excerpt)

```
## Goal
Prevent `/goal` and Ralph-style loops from silently burning context by enforcing token budgets and escalation rules.

## Context
Autonomous loops can repeatedly add shell output, summaries, test logs, and planning text. Hermes Turbo needs a budget governor that chooses compression, summarization, or expansion deliberately.

## Acceptance criteria
- Add configurable budgets per turn, per loop, per tool result, and per session.
- Warn or switch compression mode when a budget is close to being exceeded.
- Prefer focused tests/logs before full-output expansion.
- Add policy hooks for high-risk tasks where more context is worth the cost.
- Include tests for budget decisions and loop behavior.
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
