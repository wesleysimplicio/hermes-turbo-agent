# Issue #84: Evaluate optional Rust or Tokio sidecar for high-concurrency gateway paths

Tracking PR scaffold. Reopened because previous closure had no commits.

## Source
- Repo: wesleysimplicio/hermes-turbo-agent
- Issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/84

## Original description (excerpt)

```
## Goal
Explore a credible path to close the pure async scheduler gap where Node/libuv still wins.

## Context
`uvloop` improves real Python async paths, but the README and win plan acknowledge that a synthetic 1,000-task scheduler benchmark can still favor OpenClaw. A Rust/Tokio sidecar may be the right optional architecture for high-concurrency gateway workloads.

## Acceptance criteria
- Write an ADR comparing pure Python/uvloop, Node/libuv, and Rust/Tokio sidecar options.
- Identify which gateway paths would benefit without complicating normal CLI usage.
- Prototype only if the ADR shows a clear, bounded path.
- Keep the sidecar optional and disabled by default.
- Define benchmark and correctness gates before implementation.
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
