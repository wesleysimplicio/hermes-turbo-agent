# Issue #101: Optimize output-token usage with concise response contracts

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/101

## Original description (excerpt)

```
## Goal
Reduce latency and cost by generating fewer output tokens in autonomous loops, status updates, and tool summaries.

## Acceptance criteria
- Add concise response contracts for loop status, tool summaries, PR updates, and issue comments.
- Use structured fields instead of verbose prose for machine-facing loops.
- Preserve human-readable summaries for final reports.
- Track output-token savings separately from input-token savings.
- Add tests for summary completeness.
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
