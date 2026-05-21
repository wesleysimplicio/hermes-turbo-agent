# Issue #96: Add provider prompt-cache boundary and live regression tests

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/96

## Original description (excerpt)

```
## Goal
Beat OpenClaw's prompt-cache discipline by making Hermes Turbo cache boundaries explicit, provider-aware, and regression-tested.

## Acceptance criteria
- Split stable prompt prefix from volatile runtime suffix.
- Keep tools, skills metadata, project maps, and static policy byte-stable where possible.
- Move timestamps, heartbeat, runtime status, and per-turn metadata after the cache boundary.
- Add OpenAI and Anthropic cache usage tracking where providers expose it.
- Add live or opt-in regression tests for repeated stable prefixes and tool transcripts.
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
