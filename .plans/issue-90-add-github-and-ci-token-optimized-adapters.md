# Issue #90: Add GitHub and CI token-optimized adapters

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/90

## Original description (excerpt)

```
## Goal
Make GitHub issue/PR/check workflows token-efficient by summarizing the high-signal parts of `gh` and CI output.

## Context
A lot of agent token burn comes from `gh issue view`, `gh pr view`, `gh pr checks`, `gh run view --log`, and verbose CI logs. Hermes Turbo should prefer compact summaries and let the agent expand only the failing step or relevant thread.

## Acceptance criteria
- Add adapters for `gh issue list/view`, `gh pr list/view/checks`, and GitHub Actions logs.
- Group CI failures by job, step, file, line, and error signature.
- Strip duplicated logs, progress noise, and low-signal metadata.
- Preserve links, issue/PR numbers, check names, failing commands, and timestamps when relevant.
- Add fixtures for noisy GitHub/CI output and compression tests.
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
