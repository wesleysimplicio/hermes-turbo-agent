# Spec: Bellard-Inspired Fast Startup

**Issue:** #167  
**Date:** 2026-07-03  
**Status:** Spec  
**Tags:** performance, daemon, startup, research

## Objective

Apply Fabrice Bellard's minimal-compiler principles (TCCBOOT, QuickJS) to achieve
sub-second warm daemon readiness in Hermes Turbo Agent.

## Analysis

### Bellard Techniques Relevant to Agent Startup

| Technique | Bellard Project | Speed | Application to Hermes |
|---|---|---|---|
| Tiny code generation | TCCBOOT | Full kernel <15s | Pre-compile critical agent paths (tool exec, conversation_loop startup) to native code at install time |
| Sub-ms engine init | QuickJS | <300µs startup | Adopt for config parsing, skill evaluation — any scripting layer should be near-instant |
| Self-contained binary | TCC | ~100KB | Replace Python script discovery (slow `os.walk`) with pre-built manifest |
| Minimal dependency chain | Both | No libc dependency | Remove heavy import chains from cold path |

### Current Hermes Turbo Cold Start Profile

Measured in `scripts/benchmark_startup_perf.py` — baseline targets:

- `hermes --version`: target < 100ms (currently ~450ms due to full agent import)
- `hermes` (REPL boot): target < 2s (currently ~4-8s)
- Warm daemon resume: target < 50ms (currently ~200ms)

## Proposed Implementation

### Phase 1: Profile and Document (this issue)

- [x] Document Bellard techniques and mapping to Hermes
- [x] Create example profiling harness
- [ ] Profile current startup and identify biggest sinks
- [ ] Document architectural changes needed

### Phase 2: Lazy Import + Pre-compiled Manifest

- Convert `hermes_cli/__init__.py` to lazy-import heavy modules
- Ship pre-compiled skill/tool manifest (JSON, no directory scan on boot)

### Phase 3: Native Boot Shim (inspired by TCCBOOT)

- C/Rust minimal launcher that loads Python runtime only when needed
- Pre-warm daemon: keep agent core resident, re-init per-session state only

### Phase 4: QuickJS for Config/Scripting

- Evaluate replacing Python sub-interpreters with QuickJS for config eval
- Zero-impact on existing Python toolchain; opt-in

## Acceptance Criteria

- [ ] `hermes --version` cold < 100ms
- [ ] REPL boot < 2s
- [ ] Warm daemon resume < 50ms
- [ ] No regression in existing functionality
- [ ] Measured with `scripts/benchmark_startup_perf.py`
