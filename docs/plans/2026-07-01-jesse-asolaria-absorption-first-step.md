---
title: "plan: Jesse/Asolaria absorption first step — watcher verification via hermes status"
status: active
date: 2026-07-01
type: plan
target_repo: hermes-turbo-agent
origin: Jesse/Asolaria findings synthesis
---

# plan: Jesse/Asolaria absorption first step — watcher verification via hermes status

## Summary

The repo already has broad local work in flight, but the Jesse/Asolaria absorption is not yet easy to point to from one durable artifact. The first low-risk step is to make **watcher verification** explicit and operator-visible instead of implicit in logs or JSON files.

This plan treats the current `hermes status` gateway receipts surface as the first concrete absorption step because it is:

- small in scope,
- easy to verify locally,
- additive rather than destructive,
- directly tied to runtime truth (`restart_loop.json` and `dead_targets.json`), and
- a prerequisite for stronger claims discipline later.

---

## Verified current state

At the time of writing, the working tree already contains local status-surface work in these files:

- `hermes_cli/status.py`
- `tests/hermes_cli/test_status.py`

That work surfaces two gateway watcher receipts in `hermes status`:

1. **Resume gate** — whether the gateway auto-resume breaker has tripped.
2. **Dead targets** — how many delivery targets have been confirmed dead and recorded.

This is the best current candidate for a first absorbed Jesse/Asolaria step because it converts hidden runtime state into a human-verifiable operator surface.

---

## First absorbed step

### Goal

Make watcher state part of the normal operator contract:

- runtime watcher state must be visible without opening JSON files,
- operator claims about gateway health must point to `hermes status`, and
- tests must prove the visible surface matches the recorded watcher receipts.

### Contract

`hermes status` should show, in the Gateway section:

- `Resume gate: clear` when there is no recent restart-loop trip,
- `Resume gate: TRIPPED (...)` when the recorded interrupted boots exceed the breaker threshold inside the current time window,
- `Dead targets: N recorded` where `N` is the number of entries persisted in `dead_targets.json`.

### Why this is the right first step

This is not yet the full Jesse/Asolaria absorption. It is the smallest real slice that establishes the direction:

- **claims discipline** starts when operators can cite a stable status surface;
- **watcher verification** becomes testable rather than anecdotal;
- **execution state** gets a visible foothold in the CLI;
- later typed handoff / runtime-ledger work can build on a proven receipt surface.

---

## Files and evidence

### Current implementation surface

- `hermes_cli/status.py`
- `tests/hermes_cli/test_status.py`

### Runtime receipt inputs

- `<HERMES_HOME>/gateway/restart_loop.json`
- `<HERMES_HOME>/gateway/dead_targets.json`

### Local proving command

```bash
pytest tests/hermes_cli/test_status.py -q
```

This should prove both:

- the default clear/zero surface, and
- the tripped/non-zero receipt surface.

---

## Non-goals for this first step

The following are intentionally **not** part of this first absorption slice:

- typed handoff payloads between subsystems,
- a canonical `execution_state` object shared across runtime components,
- append-only runtime ledger receipts,
- claim freshness / stale-claim invalidation,
- cross-surface propagation into dashboard, TUI, or web API.

Those remain follow-on integrations after the watcher verification surface is stable.

---

## Next integrations to land after this step

1. **Claims discipline**
   - Any human-facing claim about gateway health should cite the `hermes status` watcher rows or the underlying receipt file.

2. **Typed handoff**
   - Replace ad-hoc JSON interpretation with a small typed contract for watcher receipts.

3. **Shared execution state**
   - Promote watcher summaries into a reusable runtime status object instead of recomputing them only inside the CLI.

4. **Runtime ledger**
   - Move from point-in-time status to append-only receipts for state transitions (trip, clear, target-dead, target-recovered).

5. **Broader status propagation**
   - Reuse the same verified surface in dashboard/TUI/web endpoints so operator truth is consistent everywhere.

---

## Acceptance criteria

- [ ] `hermes status` surfaces gateway watcher receipts without requiring manual inspection of JSON files.
- [ ] A focused local pytest command proves both clear and tripped watcher states.
- [ ] The first absorbed step is documented in one durable file so the repo has explicit evidence of Jesse/Asolaria direction.
- [ ] Follow-on work is clearly separated from this first step to keep scope low-risk.

---

## Decision

Adopt **watcher verification via `hermes status`** as the first explicit Jesse/Asolaria absorption step in `hermes-turbo-agent`, and treat claims discipline / typed handoff / runtime-ledger as follow-on layers rather than folding them into the same change.
