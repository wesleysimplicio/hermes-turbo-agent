# Issue #88: Add native token-saver proxy for shell and tool output

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/88

## Original description (excerpt)

```
## Goal
Add a Hermes Turbo native token-saver layer inspired by RTK-style CLI output compression, reducing noisy shell/tool output before it enters model context.

## Context
RTK (`rtk-ai/rtk`) positions itself as a CLI proxy that rewrites common commands and compresses outputs such as `git status`, `git diff`, test runners, Docker, Kubernetes, and GitHub CLI. Hermes Turbo should offer a native equivalent for its own runtime instead of relying only on external hooks.

## Acceptance criteria
- Add a token-saver abstraction for command/tool output before it is appended to conversation context.
- Support command-aware adapters for at least `git status`, `git diff`, `git log`, `rg`, `pytest`, `ruff`, `npm test`, and generic long logs.
- Provide modes: `off`, `safe`, `balanced`, and `aggressive`.
- Preserve error details and file/line references in `safe` and `balanced` modes.
- Include tests proving compressed output keeps the actionable signal needed for debugging.
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
