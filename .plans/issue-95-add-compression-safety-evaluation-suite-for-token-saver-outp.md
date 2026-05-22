# Issue #95: Add compression safety evaluation suite for token saver outputs

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/95

## Original description (excerpt)

```
## Goal
Ensure token compression does not hide the exact information needed to fix bugs, review code, or close issues.

## Context
A token-saver is only useful if it preserves debugging signal. Hermes Turbo needs regression fixtures that compare raw output against compressed output for common workflows.

## Acceptance criteria
- Add fixtures for failing tests, lint errors, type errors, CI logs, diffs, grep output, GitHub PR reviews, and long logs.
- Define required retained signals for each fixture type.
- Test `safe`, `balanced`, and `aggressive` modes separately.
- Include adversarial cases such as repeated errors with one unique root cause, warnings before fatal errors, and secret-like values.
- Add a contributor guide for writing new compression adapters safely.
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
