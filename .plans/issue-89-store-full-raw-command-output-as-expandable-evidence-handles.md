# Issue #89: Store full raw command output as expandable evidence handles

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/89

## Original description (excerpt)

```
## Goal
Reduce tokens without losing auditability by storing full command output outside the model context and giving the agent compact handles it can expand on demand.

## Context
A token-saver can become dangerous if it hides important details. Hermes Turbo should keep full raw output in local artifacts/session storage while sending compact summaries to the model.

## Acceptance criteria
- Save raw command/tool output to a session artifact store with stable IDs.
- Return compact context output containing summary, key errors, exit code, and an `expand` handle.
- Add a tool or command to retrieve full output by handle.
- Redact secrets before storing and before summarizing.
- Include tests for retrieval, redaction, truncation, and failure cases.
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
