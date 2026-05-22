# Issue #92: Implement context working set with expand-on-demand retrieval

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/92

## Original description (excerpt)

```
## Goal
Avoid loading whole repositories, files, logs, and histories into context when the agent only needs a small working set.

## Context
Token economy is not only command-output compression. Hermes Turbo should maintain a compact working set of relevant files, symbols, diffs, tests, and issue facts, then expand only when needed.

## Acceptance criteria
- Add a context working-set model for current task facts, files, symbols, diffs, commands, and evidence handles.
- Prefer snippets, signatures, and summaries over full files by default.
- Add explicit expansion APIs for full file, wider snippet, full diff, full log, or raw evidence.
- Integrate with existing skill/project indexing where available.
- Include tests that large inputs stay under configured token budgets.
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
