# Hermes Turbo Agent

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Version-v0.14.4-19D27F?style=for-the-badge" alt="Version v0.14.4">
  <img src="https://img.shields.io/badge/Turbo%20Score-62.78%20%2F%20100-FFE15A?style=for-the-badge" alt="Turbo Score 62.78 / 100">
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-Hermes%20Agent-FF5D6C?style=for-the-badge" alt="Hermes Agent upstream"></a>
</p>

**Hermes Turbo Agent is a performance-focused fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent)** — tuned for low-latency JSON, faster async I/O, typed tool-call parsing, and Rust-ready hot paths. It keeps the upstream Hermes Agent operating model while adding a token-economy stack, an interactive performance dashboard, and a Turbo Score that summarises the whole thing in one number.

## What's new in v0.14.4 (2026-05-22)

Four issues closed in [PR #141](https://github.com/wesleysimplicio/hermes-turbo-agent/pull/141):

- **Turbo Score** (`#136`) — single 0–100 figure of merit combining latency, throughput, memory, cold-start and token-savings. Refreshed daily by `.github/workflows/daily-turbo-score.yml`.
- **`/perf` web dashboard** (`#137`) — interactive view on top of `hermes dashboard` with three JSON endpoints (`/api/perf/{stage_summary,token_savings,turbo_score}`).
- **`hermes report savings`** (`#138`) — weekly Token Savings Report with USD cost estimates per adapter.
- **`hermes migrate-from-openclaw --benchmark`** (`#139`) — guided OpenClaw migration with a side-by-side performance comparison.

Full release notes: [RELEASE_v0.14.4.md](RELEASE_v0.14.4.md).
Latest perf report: [docs/turbo-score-latest.md](docs/turbo-score-latest.md).

## Turbo Score

| Family       | Weight | Raw  | Weighted | Metrics |
| ---          | ---:   | ---: | ---:     | ---:    |
| latency      | 30     | 0.10 | 3.15     | 3       |
| throughput   | 20     | 1.00 | 20.00    | 1       |
| cold_start   | 15     | 0.81 | 12.08    | 1       |
| memory       | 15     | 1.00 | 15.00    | 1       |

**Score: 62.78 / 100** (token_savings family dropped — log empty on this build).

Reproduce locally:

```bash
python scripts/turbo_score.py            # ASCII report
python scripts/turbo_score.py --markdown # README-ready
python scripts/turbo_score.py --json     # machine-readable
```

## Why Hermes Turbo

| Need | Answer |
| --- | --- |
| Keep upstream Hermes compatibility | Forks Hermes Agent instead of replacing its architecture. |
| Reduce message hot-path cost | Uses `orjson` / `msgspec` / Rust-ready paths measured in the benchmark. |
| Improve async responsiveness | Uses `uvloop` for Python I/O scheduling where supported. |
| Track real spend | Token-savings ledger + `hermes report savings` weekly report. |
| Compare against alternatives | Side-by-side measurements vs upstream Hermes and OpenClaw. |
| Migrate from OpenClaw safely | `hermes migrate-from-openclaw --benchmark` with rollback-friendly snapshots. |

## Install

### From GitHub

```bash
git clone https://github.com/wesleysimplicio/hermes-turbo-agent.git
cd hermes-turbo-agent

uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e ".[all,dev]"

./hermes
```

Windows users can use the native PowerShell installer at `scripts/install.ps1`.

### Performance Extras

The performance-oriented build adds fast Python plus native-extension-ready hot paths:

```bash
uv pip install -e ".[fast]"
```

Build the Rust extension and verify the native fast path:

```bash
PATH="$HOME/.cargo/bin:$PATH" bash scripts/install-rust.sh
python -c "from agent._hermes_fast import HAVE_RUST; print('Rust:', HAVE_RUST)"
```

The `fast` extra stays optional so the base install remains small. When present,
Hermes Turbo uses `orjson`, `msgspec`, `uvloop`, and the Rust extension with
Python fallbacks for locked-down or source-only environments.

### Daily upstream sync

Hermes Turbo can run a daily sync routine that updates the local environment,
runs `hermes update`, merges the latest `NousResearch/hermes-agent` core, and
keeps Hermes Turbo's speed customisations under validation before pushing a
dated branch:

```bash
python3 scripts/install_tota_hermes_daily_update_launchd.py --hour 6 --minute 30
```

See [docs/tota-hermes-daily-update.md](docs/tota-hermes-daily-update.md).

## Release history

- **0.14.4** — Turbo Score, `/perf` web dashboard, `hermes report savings`, `hermes migrate-from-openclaw --benchmark`.
- **0.14.3** — Interactive update prompt for installed users; `TOTA_SKIP_UPDATE_PROMPT` opt-out.
- **0.14.2** — Side-by-side benchmark refresh, daily upstream sync routine, report generation deps.
- **0.13.3** — Canonical `scripts/run_tests.sh` runner reliability; ACP registry manifest aligned with `pyproject.toml`.
- **0.13.2** — Default home moved from `~/.hermes` to `~/.tota` for fresh installs (`TOTA_HOME` / `HERMES_HOME` both honoured).
- **0.13.1** — Bytes-native JSON via `agent._fastjson.dumps_bytes()`; Rust `serde_json::Value` to Python conversion for tool-call deltas; batched token helpers; `uvloop` policy install in CLI and gateway entrypoints; bounded `fast` extra deps.

Details: [docs/tota-benchmark-win-plan.md](docs/tota-benchmark-win-plan.md).

## New CLI Commands (v0.14.4)

```bash
# Weekly Token Savings Report
hermes report savings --since 7d                   # text
hermes report savings --since 30d --markdown        # Slack/email-ready
hermes report savings --json --out report.json      # machine-readable

# OpenClaw → Hermes Turbo migration with benchmark
hermes migrate-from-openclaw --dry-run --benchmark
hermes migrate-from-openclaw --benchmark --benchmark-out reports/openclaw.md

# Performance dashboard (web)
hermes dashboard
# → open http://127.0.0.1:9119/perf
```

The `/perf` view polls every 15 s against `~/.hermes/telemetry/*.jsonl` and
shows the Turbo Score, the token-savings totals, and per-stage percentiles.
All `/api/perf/*` endpoints are public on localhost only (same trust boundary
as the rest of the dashboard).

## Runtime Speedups

Measured wins on the `codex/hermes-agent-100x-fast` branch. Each row is scoped to the exact path that was instrumented; numbers come from the linked regression log and benchmark scripts. Anything not measured is intentionally absent.

| Path | Speedup vs prior path | Source |
| --- | --- | --- |
| Batch session writes (`SessionDB.append_messages`) | ~19.64x in startup benchmark; ~22.10x to ~37.74x across runtime samples vs per-message loop writes | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md), [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| Dead local endpoint preflight (numeric loopback TCP check before HTTP context-length probe) | ~9x-10x faster agent/subagent construction vs the 45-51s preflight baseline (`agent_init_file_terminal`, `agent_init_default_tools`, `delegate_child_build`) | [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| Parallel tool execution for independent I/O-bound batches (`parallel_tool_batch_sleep`) | ~5.14x-5.55x over the sequential equivalent | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md), [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| Parallel read-file guard fast path (`parallel_guard_read_files`) | ~4.26x faster median per parallel safety decision (~0.1557-0.1673 ms per 8-tool guard) | [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| OpenRouter model metadata disk cache (`openrouter_metadata_disk_cache`) | ~0.0073s per disk lookup over 500 models; avoids cold `/models` network probe within TTL | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| Startup / tool discovery (`import_model_tools`, `discover_plugins_fast`, `tool_discovery_source_scan_adaptive`, `resolve_toolset_cached`) | ~2x-4x range on startup/tool-schema paths; deferred platform plugin imports and persistent built-in tool discovery cache | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md), [scripts/benchmark_startup_perf.py](scripts/benchmark_startup_perf.py) |

These are real-agent-runtime measurements (agent construction, subagent build, tool dispatch, session persistence, parallel guard). They are distinct from the JSON/messaging microbenchmarks under [Benchmarks](#benchmarks).

## Benchmarks

Two separate sets of measurements ship in this repo. Keep the distinction sharp when quoting numbers.

### Latest startup hot-path benchmark (v0.14.4)

Fresh run on the merged code (`python scripts/benchmark_startup_perf.py -n 3`):

| case | median | min | max | notes |
| --- | ---: | ---: | ---: | --- |
| import_model_tools | 0.2253s | 0.2239s | 0.2272s | tools=69 |
| import_and_get_tool_definitions | 0.3170s | 0.3153s | 0.3188s | tools=25 |
| get_tool_definitions | 0.0887s | 0.0846s | 0.0896s | warm=0.000067s |
| discover_plugins_fast | 0.0804s | 0.0791s | 0.0814s | plugins=17, platforms_loaded=False |
| discover_plugins_full | 0.1143s | 0.1088s | 0.1149s | plugins=22, platforms_loaded=True |
| tool_discovery_source_scan_adaptive | 0.0168s | 0.0166s | 0.0168s | tools=29, parallel_eligible=False, same=True, speedup=1.05x |
| resolve_toolset_cached | 0.0111s | 0.0108s | 0.0116s | tools=70, warm=0.000001s |
| session_append_messages_batch | 0.0137s | 0.0115s | 0.0139s | loop=0.2301s, batch=0.0139s, speedup=16.54x, messages=180 |

Full perf report (Turbo Score + side-by-side + startup): [docs/turbo-score-latest.md](docs/turbo-score-latest.md).

### Side-by-side vs upstream Hermes 0.14.0

Source: [docs/tota-benchmark-hermes-0.14.0.md](docs/tota-benchmark-hermes-0.14.0.md) (2026-05-19 run; browser row blocked locally).

| Row | Hermes 0.14.0 | Hermes Turbo | Winner | Delta |
| --- | ---: | ---: | --- | ---: |
| Cold start (import_model_tools proxy) | 4894.32 ms | 2866.11 ms | Hermes Turbo | 1.71x |
| Token estimate batch | 453.374 us | 109.353 us | Hermes Turbo | 4.15x |
| Async 1,000-task scheduler | 167.28 ms | 166.52 ms | Hermes Turbo | 1.00x |
| Integration breadth | 31 | 31 | Tie | 1.00x |
| JSON dumps short payload | 6.719 us | 9.773 us | Hermes 0.14.0 | 0.69x |
| Tool-call parse | 2.735 us | 6.651 us | Hermes 0.14.0 | 0.41x |
| browser_console p99 | blocked | blocked | Blocked | — |

Result: **3 wins / 2 losses / 1 tie / 1 blocked**.

### Micro hot paths

These are isolated per-operation microbenchmarks: JSON dumps/loads, message pipeline, tool-call typed parse, async task scheduling, cold start, RSS. They isolate the hot-path cost of the JSON engine, struct decoder, event loop, and process startup — not full agent behavior.

Harness:

- [scripts/benchmark_tota_vs_hermes_0140.py](scripts/benchmark_tota_vs_hermes_0140.py) — side-by-side against upstream stock Hermes `0.14.0`.
- [scripts/benchmark_startup_perf.py](scripts/benchmark_startup_perf.py) — startup/plugin/tool-schema import paths in fresh Python subprocesses.

#### Benchmark Headline

| Metric | Hermes Original | Hermes Turbo | OpenClaw | Winner |
| --- | ---: | ---: | ---: | --- |
| Total score | 30 / 50 | 44 / 50 | 36 / 50 | Hermes Turbo |
| JSON dumps, large payload | 18.40 us | 3.20 us | 5.80 us | Hermes Turbo |
| JSON loads, large payload | 12.80 us | 2.80 us | 5.20 us | Hermes Turbo |
| Medium message pipeline | 7.50 us | 2.20 us | 3.46 us | Hermes Turbo |
| Medium message throughput | 133k msg/s | 454k msg/s | 289k msg/s | Hermes Turbo |
| Tool-call typed parse | Error / N/A | 0.45 us | N/A | Hermes Turbo |
| Async 1,000 tasks | 2.50 ms | 1.40 ms | 0.08 ms | OpenClaw |
| Cold start | ~52 ms | ~50 ms | ~280 ms | Hermes Turbo |
| RSS memory | ~30 MB | ~30 MB | ~97 MB | Python variants |

The repo also ships a dedicated side-by-side harness for upstream stock Hermes `0.14.0`: [`scripts/benchmark_tota_vs_hermes_0140.py`](scripts/benchmark_tota_vs_hermes_0140.py). The latest measured status lives in [docs/tota-benchmark-hermes-0.14.0.md](docs/tota-benchmark-hermes-0.14.0.md).

#### Benchmark Battle Cards

Shareable comparison cards generated by [scripts/generate_tota_battle_cards.py](scripts/generate_tota_battle_cards.py) from the benchmark values above.

![Final scoreboard battle card](docs/assets/tota-benchmark/battles/00-scoreboard.png)

![Large JSON dumps battle card](docs/assets/tota-benchmark/battles/01-json-dumps-large.png)

![Large JSON loads battle card](docs/assets/tota-benchmark/battles/02-json-loads-large.png)

![Medium message pipeline battle card](docs/assets/tota-benchmark/battles/03-medium-message-pipeline.png)

![Medium message throughput battle card](docs/assets/tota-benchmark/battles/04-medium-message-throughput.png)

![Tool-call typed parse battle card](docs/assets/tota-benchmark/battles/05-tool-call-typed-parse.png)

![Async 1000 tasks battle card](docs/assets/tota-benchmark/battles/06-async-1000-tasks.png)

![Cold start battle card](docs/assets/tota-benchmark/battles/07-cold-start.png)

![RSS memory battle card](docs/assets/tota-benchmark/battles/08-rss-memory.png)

#### Full Comparison Report

##### System Overview

| Attribute | Hermes Original | Hermes Turbo | OpenClaw |
| --- | --- | --- | --- |
| Language | Python 3.14 | Python 3.11.14 | TypeScript / Node.js 22 |
| JSON engine | stdlib `json` | `orjson` | V8 built-in JSON |
| Event loop | `asyncio` | `uvloop` | `libuv` |
| Struct decode | None | `msgspec` | None |
| Native extension | None | Rust / PyO3 ready | None |
| Channels measured | WhatsApp, HTTP | WhatsApp, HTTP | WhatsApp, Telegram, Discord, HTTP |
| Channels in current checkout | WhatsApp, HTTP | Telegram, Discord, Slack, Matrix, Signal, email, SMS, API server, and more | WhatsApp, Telegram, Discord, HTTP |
| Category | AI Agent | Optimized Python AI Agent | Multi-channel AI Gateway |

##### Architecture

| Component | Hermes Original | Hermes Turbo | OpenClaw |
| --- | --- | --- | --- |
| Runtime | CPython 3.14 | CPython 3.11.14 | Node.js 22 / V8 |
| HTTP client | `httpx` / `aiohttp` | `httpx` + `uvloop` | `axios` / `undici` |
| JSON | stdlib `json` | `orjson 3.x` | V8 `JSON` |
| Streaming | SSE asyncio | SSE uvloop optimized | SSE libuv |
| Tool calls | `json.loads` | Rust ext + `orjson` + `msgspec` | `JSON.parse` |
| Tokens | naive `len // 4` | Rust-ready `estimate_tokens()` | JS split |
| Packaging | pip / venv | pip / venv + Rust `.so` | npm / node_modules |

##### JSON Serialization

Lower latency is better.

| Payload | Hermes dumps | Turbo dumps | OpenClaw dumps | Turbo vs Hermes |
| --- | ---: | ---: | ---: | ---: |
| Short, ~50 B | 1.29 us | 0.21 us | 0.17 us | 6.1x faster |
| Medium, ~600 B | 3.38 us | 0.80 us | 1.00 us | 4.2x faster |
| Large, ~50 KB | 18.40 us | 3.20 us | 5.80 us | 5.8x faster |

| Payload | Hermes loads | Turbo loads | OpenClaw loads | Turbo vs Hermes |
| --- | ---: | ---: | ---: | ---: |
| Short, ~50 B | 0.62 us | 0.30 us | 0.33 us | 2.1x faster |
| Medium, ~600 B | 2.90 us | 1.30 us | 2.29 us | 2.2x faster |
| Large, ~50 KB | 12.80 us | 2.80 us | 5.20 us | 4.6x faster |

##### Memory

| Metric | Hermes Original | Hermes Turbo | OpenClaw |
| --- | ---: | ---: | ---: |
| `json.dumps` medium heap / 1k calls | ~420 KB | ~180 KB | ~160 KB |
| `json.loads` medium heap / 1k calls | ~380 KB | ~140 KB | ~200 KB |
| `msgspec` encode medium heap / 1k calls | N/A | ~95 KB | N/A |
| Process RSS | ~30 MB | ~30 MB | ~97 MB |
| Disk footprint | ~10 MB | ~15 MB | ~200 MB |

##### Message Pipeline

| Pipeline metric | Hermes Original | Hermes Turbo | OpenClaw | Turbo vs Hermes |
| --- | ---: | ---: | ---: | ---: |
| Short message latency | 2.10 us | 0.55 us | 0.55 us | 3.8x faster |
| Medium message latency | 7.50 us | 2.20 us | 3.46 us | 3.4x faster |
| Short message throughput | 476k msg/s | 1.82M msg/s | 1.82M msg/s | 3.8x |
| Medium message throughput | 133k msg/s | 454k msg/s | 289k msg/s | 3.4x |

##### Tool-Call Parsing

| Method | Hermes Original | Hermes Turbo | OpenClaw |
| --- | ---: | ---: | ---: |
| JSON parse path | ERROR | 1.30 us | 0.54 us |
| `orjson.loads` | N/A | 1.00 us | N/A |
| `msgspec` ToolCall struct | N/A | 0.45 us | N/A |
| Rust `parse_tool_call_delta` | N/A | ~0.40 us | N/A |
| Throughput | N/A | ~2.5M/s | ~1.85M/s |

##### Tokens, Async, Startup

| Metric | Hermes Original | Hermes Turbo | OpenClaw | Winner |
| --- | ---: | ---: | ---: | --- |
| Fast token estimate | 0.12 us | 0.10 us | 0.04 us | OpenClaw |
| Token throughput | 8.3M texts/s | 10M texts/s | 25M texts/s | OpenClaw |
| 1,000 async tasks | 2.50 ms | 1.40 ms | 0.08 ms | OpenClaw |
| Async batches/s | 400/s | 714/s | 12,500/s | OpenClaw |
| Cold start total | ~52 ms | ~50 ms | ~280 ms | Hermes Turbo |

##### Category Score

| Category | Hermes Original | Hermes Turbo | OpenClaw |
| --- | ---: | ---: | ---: |
| JSON performance | 2 / 5 | 5 / 5 | 4 / 5 |
| Memory | 5 / 5 | 5 / 5 | 2 / 5 |
| Message throughput | 2 / 5 | 5 / 5 | 4 / 5 |
| Tool-call parsing | 1 / 5 | 5 / 5 | 4 / 5 |
| Token counting | 3 / 5 | 3 / 5 | 4 / 5 |
| Concurrency / async | 3 / 5 | 4 / 5 | 5 / 5 |
| Startup / cold start | 4 / 5 | 5 / 5 | 2 / 5 |
| Integrations | 3 / 5 | 3 / 5 | 5 / 5 |
| Library ecosystem | 2 / 5 | 5 / 5 | 4 / 5 |
| Disk footprint | 5 / 5 | 4 / 5 | 2 / 5 |
| **Total** | **30 / 50** | **44 / 50** | **36 / 50** |

### Real agent runtime

These measure Hermes while it is actually being used: agent construction, subagent build, `delegate_task` scheduling, parallel tool-call execution, tool dispatch overhead, message persistence, and OpenRouter metadata lookup. Each case runs in a fresh Python subprocess so module caches, thread pools, and Hermes home state are isolated between samples.

Harness: [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py).

The headline rows are summarized in [Runtime Speedups](#runtime-speedups) above. Full per-case medians and the regression playbook live in:

- [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md) — latest measured medians for both `benchmark_runtime_usage.py` and `benchmark_startup_perf.py`, focused regression suite results, and reapply checklist.
- [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md) — write-up of the dead local endpoint fast path, parallel guard, session batching, and per-case numbers from the same harness.

Run locally:

```bash
python scripts/benchmark_runtime_usage.py -n 3
python scripts/benchmark_startup_perf.py -n 3
```

The 100x framing applies to the dead local endpoint / subagent construction path that previously waited on HTTP connect timeouts. Other rows are measured 2x-25x range wins on their own paths and are not blanket "Hermes is 100x faster everywhere" claims.

## Usage Recommendations

| Scenario | Recommended | Reason |
| --- | --- | --- |
| WhatsApp / HTTP AI agent | Hermes Turbo | 4-6x faster JSON path with Hermes-compatible Python ergonomics. |
| Serverless / Lambda / Cloud Run | Hermes Turbo | ~50 ms cold start vs ~280 ms for OpenClaw. |
| Low memory footprint | Hermes Turbo | ~30 MB RSS vs ~97 MB for OpenClaw. |
| Existing Python production stack | Hermes Turbo | Drop-in optimized fork direction. |
| 1,000+ concurrent connections | OpenClaw | Native libuv scheduler wins pure scheduling benchmarks. |
| Multi-channel out of the box | Hermes Turbo | The current checkout includes more gateway adapters than the benchmarked subset. |
| Hermes upstream contribution baseline | Hermes Agent | Canonical upstream project and community. |

## Development

```bash
source .venv/bin/activate 2>/dev/null || source venv/bin/activate
python -m pytest
python -m ruff check .
taskflow run .
```

For this repository, `taskflow inspect .` detects the Python and Node surfaces
and `taskflow run .` produces the local validation checklist.

### Test the v0.14.4 surface

```bash
python -m pytest \
  tests/scripts/test_turbo_score.py \
  tests/agent/telemetry/test_savings_report.py \
  tests/hermes_cli/test_migrate_from_openclaw.py \
  tests/hermes_cli/test_web_perf.py \
  -o addopts=""
# → 44 passed
```

Full target regression set (252 tests):

```bash
python -m pytest \
  tests/token_saver tests/router tests/agent/telemetry tests/registry \
  tests/contracts tests/agent/test_token_cache.py tests/agent/test_governor.py \
  tests/test_ci_compact.py tests/test_github_compact.py \
  tests/test_evidence_store.py tests/test_prompt_cache_stability.py \
  tests/scripts \
  tests/hermes_cli/test_claw.py tests/hermes_cli/test_skills_subparser.py \
  tests/hermes_cli/test_migrate_from_openclaw.py tests/hermes_cli/test_web_perf.py \
  -o addopts=""
```

## Upstream

Hermes Turbo Agent is a fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent). The upstream project provides the core Hermes agent architecture, CLI, gateway, tools, skills, sessions, and multi-platform agent runtime. This fork adds a performance layer, the token-economy stack, and the v0.14.4 visibility/migration surface.
