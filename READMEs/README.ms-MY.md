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

Executable installation and performance-optimization skill for Hermes Agent. It is a procedure, not an executable fork: it measures the active Hermes path, applies the smallest compatible change, tests it, and keeps it only when evidence supports it.

## 1. Scope and safety

The target is the active bundle at `${HERMES_HOME:-$HOME/.hermes}`. The skill must not silently modify a source checkout, discard user state, break prompt caching, add telemetry, or claim a benchmark gain that was not measured on the real path.

Every run creates a rollback point, records a baseline, applies a bounded change, runs regression tests, repeats the benchmark, and reports modified files, fallback status, and rollback instructions.

## 2. Performance modules

### Fast JSON and typed contracts

Use an internal bytes-first adapter with this order:

1. `orjson` for ordinary JSON dictionaries, lists, tool results, and cache payloads;
2. `msgspec` only for stable typed `Struct` contracts such as fixed envelopes;
3. Python `json` as the universal fallback.

The adapter must preserve `str`/`bytes` behavior, Unicode, invalid-payload errors, non-serializable values, and compatibility with existing dictionaries. It must never replace flexible parsing with a typed contract without tests.

### Native streaming parser

The Simplicio Agent comparison added a PyO3 `hermes_fast` extension for incremental JSON/tool-call parsing. Hermes Turbo may build it with `maturin`, but it remains optional and must have a `json.JSONDecoder.raw_decode` fallback.

The FFI boundary is not free. On the measured macOS Python 3.11 path, small payloads were faster with stdlib; payloads around 1 KiB and larger favored Rust. Use a target-specific size threshold and re-benchmark after changing Python, Rust, or the extension.

### Async event loop

Install `uvloop` only on supported Unix platforms and only through capability detection at async entrypoints. Keep stdlib `asyncio` for Windows, missing packages, opt-out, and installation failures. Measure cold start, warm start, latency, and throughput separately.

### Existing persistence and caches

Batch one conversation round into one SQLite transaction without changing message ordering, role alternation, or crash recovery. Cache tool discovery, schemas, and external metadata with versioning, TTL where appropriate, invalidation on configuration/skill/plugin/schema changes, atomic writes, and no secrets.

### Safe parallelism

Parallelize only independent operations. Preserve deterministic result order, bounded concurrency, timeout, cancellation, backpressure, and sequential-equivalent semantics.

## 3. Simplicio-derived candidates

The analyzed `wesleysimplicio/simplicio-agent` repository also contains a warm daemon, working-set/token memoization, deterministic routing, an async DAG executor, an HTTP pool, a TOON output codec, project mapping, and a performance-regression gate.

Working-set memoization and cache invalidation are safe candidates when the active Hermes path does not already provide them. The warm daemon is a separate lifecycle surface: do not copy it into Hermes without a daemon benchmark, idle TTL, memory bound, shutdown handling, and crash-recovery tests. The Rust token estimator is not enabled automatically because serialization and FFI can outweigh its simple arithmetic; benchmark it on the actual history shape first.

## 4. Installation workflow

1. Map the active bundle, runtime, profile, package manager, and state.
2. Create a rollback archive before mutation.
3. Capture cold/warm startup, discovery, persistence, JSON/tool parsing, async throughput, and memory baselines.
4. Detect platform and optional capabilities.
5. Install `orjson`, `msgspec`, and `uvloop` with the active runtime package manager (`uv pip` when the venv has no pip).
6. Apply one small, reviewable change to the measured bottleneck.
7. Add regression, fallback, invalid-payload, concurrency, and crash-recovery coverage.
8. Run the same benchmark in the same environment.
9. Keep the change only if tests pass and there is no compatibility, safety, memory, latency, or prompt-cache regression.
10. Write a report with packages, files, metrics, tests, fallbacks, and rollback.

## 5. Reproducible command pattern

```bash
HERMES_HOME="${HERMES_HOME:-$HOME/.hermes}"
HERMES_RUNTIME="$HERMES_HOME/hermes-agent/venv/bin/python"
uv pip install --python "$HERMES_RUNTIME" orjson msgspec
# Supported Unix platforms only:
uv pip install --python "$HERMES_RUNTIME" uvloop
```

An optional native build is allowed only after a baseline and only when the toolchain is available:

```bash
cd "$HERMES_HOME/hermes-agent/rust_ext"
source "$HERMES_HOME/hermes-agent/venv/bin/activate"
uvx --from maturin maturin develop --release
```

Do not use `uv add` or modify the source checkout's dependency manifest for an active-bundle installation.

## 6. Evidence and benchmarks

Reference numbers from another operating system or fork are not Hermes results. The report must store before/after artifacts under the active bundle and identify the exact payload, Python version, platform, iteration count, and backend.

A local result may be useful without being universal. In the macOS implementation, the measured result was approximately 2.1× for JSON decode through `fast_json`/orjson and 2.7× for a 4 KiB tool-call parser through thresholded `hermes_fast`; small parser payloads correctly remained on stdlib.

## 7. Compatibility invariants

- Keep the system prompt and prompt-cache prefix byte-stable during a conversation.
- Never insert synthetic messages or break strict role alternation.
- Preserve Python `json` and `asyncio` fallbacks.
- Keep settings in `config.yaml` and secrets in `.env`.
- Never cache secrets or add outbound telemetry without explicit opt-in.
- Preserve plugins, providers, skills, security boundaries, and external payload semantics.
- Do not force native dependencies on constrained platforms.
- Do not report an optimization as complete without tests, measured comparison, and rollback evidence.

## 8. Related files

- [`SKILL.md`](SKILL.md) — executable installation and optimization procedure.
- [`READMEs/`](READMEs/) — localized copies with this same section structure.

The goal is faster Hermes without creating an incompatible fork: less repeated work, faster parsing where it actually wins, controlled async scheduling, bounded persistence, and evidence-driven decisions.
