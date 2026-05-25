# ADR-0006: `msgspec.Struct` migration for `transports/types.py::ToolCall`

**Status:** Proposed (Sprint 2 / issue #35).
**Date:** 2026-05-18.
**Owner:** TBD (dedicated PR).

## Context

PERFORMANCE_ROADMAP.md (Phase 1 section) deferred this:

> msgspec.Struct evaluated for `agent/transports/types.py::ToolCall`
> and deferred. Rationale: 45+ read sites in `run_agent.py` rely on
> `tc.function.name` / `tc.function.arguments` (back-compat property),
> plus one mutation site (`tc.function.arguments = json.dumps(args)`
> near `run_agent.py:14999`).

A direct swap to `msgspec.Struct` would break every site that reads
`tc.function.name` / `tc.function.arguments` because msgspec Structs
use plain attribute access, not the Pydantic-style nested-model
property.

## Options

### A. Compatibility shim — Struct + `@property` (recommended)

Keep the API surface identical:

```python
import msgspec


class _ToolCallFunction(msgspec.Struct, frozen=False):
    name: str
    arguments: str


class ToolCall(msgspec.Struct, frozen=False):
    id: str
    type: str = "function"
    function: _ToolCallFunction
```

`tc.function.name` and `tc.function.arguments` still work.  The
mutation site `tc.function.arguments = json.dumps(args)` works
unchanged because Struct fields are mutable by default.

**Pros**: zero call-site changes.  Drop-in faster decoding.

**Cons**: msgspec Struct doesn't support `**dict` unpacking the way
Pydantic does — but every existing call site uses attribute access,
not dict unpacking.

### B. Full migration — break the property

Rewrite all 45+ sites to use msgspec directly without the nested
Struct.  Higher risk, larger PR.

### C. Defer indefinitely

Keep Pydantic, document that this is a known performance bottleneck.

## Decision

**Option A** — compatibility shim.  Zero call-site changes, maximum
upside, lowest risk.

## Migration plan

1. Add `msgspec>=0.21` to `[project]` dependencies (already in
   `[fast]`/`[perf]` extras).
2. Rewrite `agent/transports/types.py::ToolCall` as msgspec Struct.
3. Audit the 45 read sites: ensure none use `tc.dict()` /
   `tc.model_dump()` / `**tc.function.__dict__`.  Replace any
   surviving Pydantic-only patterns.
4. Audit the mutation site near `run_agent.py:14999`:
   ```python
   tc.function.arguments = json.dumps(args)
   ```
   Works on Struct because fields are mutable.  Confirm with a test.
5. Benchmark before/after on the streaming-tool-call assembler.

## Acceptance criteria

- 45 read sites still parse cleanly.
- The mutation site still mutates.
- Streaming-tool-call benchmark: ≥3× faster decode.
- Existing run_agent test suite: no regressions.

## References

- PERFORMANCE_ROADMAP.md (Phase 1 section).
- `agent/transports/types.py` — the migration target.
- Issue #35.
