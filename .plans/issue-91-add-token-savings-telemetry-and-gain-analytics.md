# Issue #91: Add token savings telemetry and gain analytics

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/91

## Original description (excerpt)

```
## Goal
Show how many tokens Hermes Turbo saves per command, session, project, and adapter.

## Context
RTK exposes `gain` analytics. Hermes Turbo should have its own measurable token economy story so optimization is visible and regressions are caught.

## Acceptance criteria
- Track estimated raw tokens, compressed tokens, saved tokens, and saving percentage per tool result.
- Aggregate savings by command type, adapter, session, repo, and day.
- Add CLI/report output for recent token savings.
- Store metrics without capturing secrets or full prompt content.
- Add docs explaining how to interpret token savings.
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
