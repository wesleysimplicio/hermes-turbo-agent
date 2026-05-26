# Issue #85: Build robust upstream Hermes update capture and reapply system

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/85

## Original description (excerpt)

```
## Goal
Make upstream Hermes Agent sync automatic, robust, and repeatable so Hermes Turbo Agent consistently captures original Hermes updates while preserving Turbo customizations.

## Context
The fork now depends on regularly pulling updates from `NousResearch/hermes-agent`. The existing daily sync routine and 100x reapply playbook are a good start, but the process should become a first-class system that detects upstream changes, applies them, reapplies local performance/customization patches, validates, and opens a PR with evidence.

## Acceptance criteria
- Detect new upstream Hermes commits/releases on a schedule or manual command.
- Create a dated sync branch automatically.
- Merge or rebase upstream into Hermes Turbo Agent using a documented policy.
- Reapply Turbo patches only when upstream still lacks the equivalent behavior.
- Run focused tests, performance regressions, and `taskflow run` after sync.
- Generate a sync report listing upstream commits, conflicts, skipped patches, reapplied patches, tests, benchmarks, and risks.
- Open or update a GitHub PR automatically with the report.
- Never overwrite local Hermes Turbo branding, profile distributions, home/env compatibility, release notes, or benchmark docs without explicit policy.
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
