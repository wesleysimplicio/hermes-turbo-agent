# Hermes Turbo Agent

<p align="center">
  <strong>🌍 Languages:</strong><br>
  <a href="README.md">🇬🇧 English</a> |
  <a href="READMEs/README.pt-BR.md">🇧🇷 Português</a> |
  <a href="READMEs/README.es-ES.md">🇪🇸 Español</a> |
  <a href="READMEs/README.fr-FR.md">🇫🇷 Français</a> |
  <a href="READMEs/README.de-DE.md">🇩🇪 Deutsch</a> |
  <a href="READMEs/README.it-IT.md">🇮🇹 Italiano</a> |
  <a href="READMEs/README.ja-JP.md">🇯🇵 日本語</a> |
  <a href="READMEs/README.ko-KR.md">🇰🇷 한국어</a> |
  <a href="READMEs/README.zh-CN.md">🇨🇳 简体中文</a> |
  <a href="READMEs/README.ru-RU.md">🇷🇺 Русский</a> |
  <a href="READMEs/README.pl-PL.md">🇵🇱 Polski</a> |
  <a href="READMEs/README.hi-IN.md">🇮🇳 हिन्दी</a> |
  <a href="READMEs/README.ar-SA.md">🇸🇦 العربية</a> |
  <a href="READMEs/README.he-IL.md">🇮🇱 עברית</a> |
  <a href="READMEs/README.id-ID.md">🇮🇩 Bahasa Indonesia</a> |
  <a href="READMEs/README.ms-MY.md">🇲🇾 Bahasa Melayu</a>
</p>

Executable installation and performance-optimization skill for Hermes Agent.

When installed and invoked for optimization, the skill identifies the authorized Hermes installation, installs optional accelerators, applies compatible changes, runs tests, and compares before/after benchmarks. It is not an executable Hermes fork.

## What this skill recommends

### `orjson`

Evaluate `orjson` on hot JSON serialization and deserialization paths, such as messages, schemas, and tool calls.

Expected benefits:

- lower `json.loads` and `json.dumps` latency;
- lower CPU cost for medium and large payloads;
- higher message-processing throughput;
- potentially fewer allocations on frequent paths.

Usage must be encapsulated and retain a fallback to the standard `json` library.

### `msgspec`

Evaluate `msgspec` for typed parsing of messages and tool calls with stable contracts.

Expected benefits:

- faster and more predictable parsing;
- lower validation and conversion overhead;
- lower memory usage for typed structures;
- clearer detection of invalid payloads.

It must not replace flexible parsing without compatibility tests using real payloads.

### `uvloop`

Evaluate `uvloop` as an optional event loop for the CLI and gateway on supported platforms.

Expected benefits:

- better asynchronous task scheduling;
- lower latency for I/O operations;
- higher throughput in highly concurrent scenarios;
- better gateway responsiveness under load.

`asyncio` remains the official fallback. Gains must be measured per operating system.

## Other recommendations

### Batched persistence

Group the events from one round and persist them in a single SQLite transaction.

Benefits:

- fewer I/O operations;
- lower transaction overhead;
- lower session-save latency;
- better efficiency in conversations with many messages.

Ordering, role alternation, and crash recovery must remain intact.

### Startup and tool discovery

Separate metadata discovery from effective imports and cache schemas with versioning.

Benefits:

- lower cold-start time;
- less repeated work when Hermes starts;
- faster loading of tools and plugins;
- fewer unnecessary imports.

The cache must be invalidated when the version, configuration, skills, plugins, or tools change.

### External metadata cache

Use a local cache with TTL, a versioned schema, and atomic writes.

Benefits:

- fewer network calls;
- faster responses for catalogs and metadata;
- greater resilience when an external service is unavailable;
- lower startup and query cost.

Caches must never store secrets or sensitive data.

### Safe parallelism

Run operations in parallel only when they are demonstrably independent.

Benefits:

- lower total time for independent operations;
- better use of I/O;
- greater responsiveness in multi-tool flows;
- less waiting caused by unnecessary sequential work.

The implementation must preserve deterministic ordering, concurrency limits, timeouts, cancellation, and semantics equivalent to the sequential path.

## How much can it improve

The figures below are benchmark references from the former Hermes Turbo Agent fork. They are not guaranteed gains for current Hermes and must be reproduced on the real path before being treated as project results.

| Measured path | Observed gain in fork benchmark |
| --- | ---: |
| JSON serialization with large payloads | approximately 4x–6x |
| JSON deserialization with large payloads | approximately 4x |
| Medium-message latency | approximately 3x |
| Medium-message throughput | approximately 3x–4x |
| Typed tool-call parsing | up to approximately 2x–5x, depending on method |
| Batched session writes | approximately 19x–38x on the instrumented path |
| Cached metadata queries | approximately 0.007 s per query in the measured scenario |
| Startup and tool discovery | approximately 2x–4x in the measured scenario |
| Subagent construction with dead local preflight | approximately 9x–10x on the specific measured path |
| Parallel execution of independent operations | approximately 4x–5x in the measured scenario |

These values depend on payload, hardware, operating system, Python version, model, tool count, concurrent load, and the exact path measured. They must not be turned into a promise of “100x” for Hermes as a whole.

## Expected general benefits

- shorter startup time;
- faster responses in multi-tool flows;
- lower CPU and I/O cost;
- higher message throughput;
- lower memory use in typed structures;
- better asynchronous scalability;
- fewer repeated external calls;
- native acceleration without sacrificing portability;
- regression diagnosis with reproducible metrics.

## How the skill works

1. Map the project and active Hermes installation.
2. Confirm branch, working state, and authorized scope.
3. Measure cold start, warm start, tool discovery, persistence, parsing, and memory.
4. Identify the dominant bottleneck.
5. Apply one small change per cycle.
6. Add a regression test and fallback.
7. Run before/after benchmarks in the same environment.
8. Reject the change if there is a functional, security, compatibility, or prompt-caching regression.
9. Deliver a report, metrics, diff, and rollback instructions.

## Compatibility guarantees

- `orjson`, `msgspec`, and `uvloop` are optional;
- standard `json` and `asyncio` remain available as fallbacks;
- the system prompt and prompt-cache prefix remain stable during a conversation;
- message role alternation is not changed;
- behavioral settings stay in `config.yaml`;
- no secrets are included in caches;
- no external telemetry is added without opt-in;
- publishable changes should be small and reviewable.

## Conclusion

Hermes Turbo Agent is an evidence-driven optimization strategy. The greatest benefit does not come from one library, but from combining less I/O, less startup work, more efficient parsing, correct caching, and safe parallelism.

The goal is to make Hermes faster without turning it into an incompatible fork, requiring Rust or native dependencies, or sacrificing security, portability, or prompt-cache stability.
