# Issue #82: Add runtime performance dashboard and stage telemetry

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/82

## Original description (excerpt)

```
## Goal
Expose where time is spent during real Hermes Turbo Agent runs.

## Context
To keep improving speed, the project needs visibility into context build, prompt build, model calls, tool dispatch, DB writes, MCP reloads, delegation, retries, and UI event bursts.

## Acceptance criteria
- Add structured timing events for major runtime stages.
- Preserve privacy by avoiding prompt/secret capture in telemetry payloads.
- Add a local dashboard or report view that shows stage timings per run.
- Include provider/model/tool breakdowns when available.
- Add docs explaining how to use telemetry to diagnose slow runs.
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
