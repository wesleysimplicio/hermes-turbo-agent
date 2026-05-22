# Issue #81: Add warm daemon mode for desktop and car profiles

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/81

## Original description (excerpt)

```
## Goal
Make Hermes Turbo Agent feel instant in desktop and car variants by keeping expensive runtime state warm.

## Context
The new `desktop` and `car` distributions should not pay full startup/discovery cost for every interaction. A local daemon can keep registry, skill index, provider metadata, MCP fingerprints, and session DB state warm.

## Acceptance criteria
- Define a daemon architecture for desktop and car profile use.
- Preload safe caches: tool registry, skill index, provider metadata, MCP/config fingerprints, and recent session summaries.
- Add health/status commands for the daemon.
- Add safe invalidation when config, plugin, skills, or tool files change.
- Document fallbacks when daemon is not running.
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
