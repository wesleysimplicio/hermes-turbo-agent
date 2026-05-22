# Issue #99: Add no-LLM deterministic router for trivial runtime decisions

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/99

## Original description (excerpt)

```
## Goal
Avoid LLM calls for deterministic decisions such as command classification, output summarization routing, cache invalidation, and validation plan selection.

## Acceptance criteria
- Identify decisions currently using model calls or heavy context where rules are sufficient.
- Add deterministic routing for token-saver adapter selection and validation scope selection.
- Add metrics for avoided model calls.
- Include fallback to LLM only when rules are uncertain.
- Add regression tests for routing decisions.
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
