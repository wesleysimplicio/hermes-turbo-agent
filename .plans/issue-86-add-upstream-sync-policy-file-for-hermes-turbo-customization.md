# Issue #86: Add upstream sync policy file for Hermes Turbo customizations

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/86

## Original description (excerpt)

```
## Goal
Codify what the upstream sync system should keep, prefer, merge, or regenerate during Hermes Agent updates.

## Context
A robust update system needs policy, not only scripts. The fork has branding, aliases, desktop/car profiles, performance patches, benchmark docs, and compatibility layers that must survive upstream refreshes.

## Acceptance criteria
- Add a machine-readable sync policy file under docs or config.
- Classify paths as `keep-turbo`, `prefer-upstream`, `merge`, `regenerate`, or `manual-review`.
- Include explicit rules for branding, CLI aliases, profile distributions, `HERMES_TURBO_HOME`, benchmark docs/assets, and performance patches.
- Add validation that the policy references existing paths or accepted glob patterns.
- Document how to update the policy when new fork-owned areas are added.
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
