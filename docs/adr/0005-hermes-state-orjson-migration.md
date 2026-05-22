# ADR-0005: `hermes_state.py` orjson migration with SQLite round-trip audit

**Status:** Proposed (Sprint 2 / issue #37).
**Date:** 2026-05-18.
**Owner:** TBD (dedicated, high-risk PR).

## Context

`hermes_state.py` (~3,000 LOC, 130 KB) implements the FTS5-backed
SQLite SessionDB.  It serialises agent state to disk on every message
and reads it back on session reload.  Migrating its JSON path to
orjson is potentially a 60–80% I/O win, but carries the highest
breakage risk in the codebase:

- **SQLite round-trip safety** — bytes-identical persistence matters.
  orjson and stdlib disagree on subtle cases (NaN, Infinity, very large
  ints, escaped surrogates).
- **Windows TOCTOU semantics** — a recent fix (`7fee1f61e`) locked
  down concurrent reader/writer behaviour on Windows.  The migration
  cannot change file lock acquisition order or timing.

## Feature-flag rollout

Ship behind `TOTA_FAST_STATE=1`.  Default: OFF for at least one full
release cycle.  Operators opt in.

```python
import os

_USE_FAST_STATE = (
    (os.environ.get("TOTA_FAST_STATE") or "").strip().lower()
    in {"1", "true", "yes", "on"}
)

if _USE_FAST_STATE:
    from agent._fastjson import loads as _state_loads, dumps as _state_dumps
else:
    from json import loads as _state_loads, dumps as _state_dumps
```

## Audit checklist

Before flipping the default to ON:

- [ ] Identify every JSON column read/write in the SQLite layer.
- [ ] For each column, fixture a representative row (nested unicode,
      surrogate pair, NaN/Infinity if any, datetime, very large int).
- [ ] Round-trip test: stdlib write → orjson read; orjson write →
      stdlib read.  Both must produce byte-equal Python objects.
- [ ] Replay every test session under `tests/run_agent/` against the
      orjson path.  Compare snapshots.
- [ ] Stress test on Windows: 16 concurrent writers + 16 readers, two
      machines, 24 hours.  No data loss, no lock contention errors.

## Files to touch

- `hermes_state.py` (entry points + serialise/deserialise helpers).
- `tests/test_hermes_state*.py` (new round-trip + Windows-lock tests).
- `pyproject.toml` (no new extras — `orjson` already in `fast`/`perf`).

## Decision deferrals

These need explicit operator sign-off before flipping the default:

- Migration of NaN/Infinity values: stdlib defaults to allowing them,
  orjson refuses without `OPT_NON_STR_KEYS`.  Plan: explicitly reject
  NaN/Infinity at the column level (none of our schemas legitimately
  use them).
- Datetime serialisation: stdlib serialises datetimes via `default=`
  callback to ISO strings; orjson has native datetime support but uses
  a different precision.  Plan: explicit `OPT_NAIVE_UTC | OPT_OMIT_MICROSECONDS`
  for byte-equal output with our current callback.

## Acceptance criteria

- Round-trip test suite: zero diffs across all fixture sessions.
- Windows stress test: 24h clean run.
- Feature flag OFF by default; documentation explicitly says "this
  is a beta — file an issue if anything looks off."

## References

- PERFORMANCE_ROADMAP.md (Phase 1.5 section).
- `hermes_state.py` (the migration target).
- Recent fix `7fee1f61e` (TOCTOU lock semantics on Windows).
- Issue #37.
