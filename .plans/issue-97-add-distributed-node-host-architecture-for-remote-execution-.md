# Issue #97: Add distributed node host architecture for remote execution parity

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/97

## Original description (excerpt)

```
## Goal
Close the OpenClaw Gateway + Nodes advantage with a Hermes Turbo node-host architecture for remote execution, browser, desktop, and car surfaces.

## Acceptance criteria
- Define Gateway/daemon/client/node roles for Hermes Turbo.
- Add a typed node capability registry for `system.run`, browser, screen, location, notifications, and platform-specific commands.
- Include pairing/auth/approval requirements.
- Keep node execution isolated from the model-facing agent loop.
- Add an ADR and prototype plan before production implementation.
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
