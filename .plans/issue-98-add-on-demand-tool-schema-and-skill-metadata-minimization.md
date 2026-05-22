# Issue #98: Add on-demand tool schema and skill metadata minimization

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/98

## Original description (excerpt)

```
## Goal
Reduce prompt size by exposing only relevant tools and compact skills metadata per turn, while allowing discovery when needed.

## Acceptance criteria
- Add a policy for visible tool schemas by task, profile, channel, and provider.
- Add compact skill metadata with explicit character/token budgets.
- Provide expansion/discovery APIs for hidden tools/skills.
- Add tests proving irrelevant tools are not included in model prompt assembly.
- Track token savings from schema minimization.
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
