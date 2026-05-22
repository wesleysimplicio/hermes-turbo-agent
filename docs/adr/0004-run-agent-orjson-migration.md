# ADR-0004: `run_agent.py` orjson migration plan

**Status:** Proposed (Sprint 2 / issue #36).
**Date:** 2026-05-18.
**Owner:** TBD (dedicated PR).

## Context

`run_agent.py` has 48 `json.loads` / `json.dumps` call sites. Migrating
them to `agent._fastjson` (which routes to orjson when available, with
a stdlib fallback) gives a 2–10× speedup on the streaming-tool-call and
context-compression hot paths.

PERFORMANCE_ROADMAP.md deferred this from Phase 1 because some call
sites use kwargs orjson doesn't accept (`strict=False`,
`separators=(",", ":")`).  Phase 1.5 must do a per-site audit.

## Call-site audit

### Tier A — safe migrations (~30 sites)

Pure `json.loads(s)` or `json.dumps(x)` or `json.dumps(x, ensure_ascii=False)`
or `json.dumps(x, default=str)`.  `agent._fastjson` already handles all
three via the `ensure_ascii=False` (orjson default) and the `default=`
callback path.  Migrate by:

```python
- function_args = json.loads(tool_call.function.arguments)
+ from agent._fastjson import loads as _fastjson_loads
+ function_args = _fastjson_loads(tool_call.function.arguments)
```

Top candidates (per-message hot path):

- `run_agent.py:402` — tool-call argument parse (every tool call)
- `run_agent.py:4266` — message content parse
- `run_agent.py:4917` — tool-call argument parse (different code path)
- `run_agent.py:4952` — tool-content parse
- `run_agent.py:10484` — existing-text serialise
- `run_agent.py:10996` — tool-call argument parse (third code path)
- `run_agent.py:11395` — tool-call argument parse (fourth code path)
- `run_agent.py:11431` — args_str dump
- `run_agent.py:11515` — error JSON dump

### Tier B — keep stdlib (`strict=False`)

orjson does not accept `strict=False`.  These sites parse local-model
output that may contain unescaped control characters inside JSON string
values (most common local-model repair case).  Stdlib's `strict=False`
mode is the only path that handles these.

- `run_agent.py:844` — `_repair_tool_call_arguments`

**Action:** keep `json.loads(raw_stripped, strict=False)` unchanged.
Add a clarifying comment pointing to this ADR.

### Tier C — needs careful review (custom separators)

`json.dumps(parsed, separators=(",", ":"))` reserialises tool-call
arguments compactly for the wire format.  orjson's default output IS
already separator-compact (no whitespace), so `agent._fastjson.dumps`
silently produces the same wire format.

- `run_agent.py:845` — compact reserialise (safe to migrate via the
  shim's separator-aware fallback)

### Tier D — `default=str` callbacks

The shim already supports `default=` via orjson's `OPT_PASSTHROUGH_*` +
manual encoder hook.  Safe to migrate.

- `run_agent.py:548` — `_json.dumps(value, default=str)` in repair
- `run_agent.py:5287, 5294` — dump_payload serialisation

## Migration plan (one PR)

1. Add `from agent._fastjson import loads as _fastjson_loads, dumps as _fastjson_dumps`
   at the top of `run_agent.py`.
2. Replace every Tier A / Tier C / Tier D site with the shim
   equivalent.  Tier B sites get a `# fastjson:keep` comment.
3. Add a regression test: parse a tool-call payload through both stdlib
   and the shim; assert byte-equal output.
4. Add a micro-benchmark in `tests/agent/test_fastjson_runagent_bench.py`
   that times the migrated hot path with and without orjson installed.

## Acceptance criteria

- Per-message tool-call parsing benchmark: ≥2× faster vs stdlib.
- Existing run_agent test suite: no regressions.
- Tier B site explicitly documented as stdlib-only.

## References

- PERFORMANCE_ROADMAP.md (Phase 1.5 section).
- `agent/_fastjson.py` — the migration target.
- Issue #36.
