# Issue #94: Add RTK compatibility and external token-saver bridge

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/94

## Original description (excerpt)

```
## Goal
Let users who already installed RTK or similar tools benefit from them while Hermes Turbo keeps a native fallback.

## Context
RTK supports Codex/Claude-style workflows by rewriting shell commands into compact proxy calls. Hermes Turbo should detect and optionally use compatible external token savers without making them mandatory dependencies.

## Acceptance criteria
- Detect whether `rtk` is installed and available.
- Add config to choose `native`, `rtk`, or `auto` token-saver backend.
- Keep native summarization as the default/fallback.
- Document setup tradeoffs and safety considerations.
- Add tests for backend selection and fallback behavior.
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
