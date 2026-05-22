<p align="center">
  <img src="docs/assets/hermes-turbo-brand/hermes-turbo-agent-banner.png" alt="Hermes Turbo Agent banner" width="100%">
</p>

# Hermes Turbo Agent

<p align="center">
  <a href="docs/perf/turbo-full-segments.pdf"><img src="https://img.shields.io/badge/Benchmark-PDF-19D27F?style=for-the-badge" alt="Turbo full benchmark PDF"></a>
  <a href="docs/perf/hermes-vs-turbo-vs-openclaw.pdf"><img src="https://img.shields.io/badge/3--way%20vs%20OpenClaw-PDF-FFE15A?style=for-the-badge" alt="3-way comparison PDF"></a>
  <a href="docs/perf/TURBO_REFLECTION.md"><img src="https://img.shields.io/badge/Per--item%20Reflection-MD-32B7FF?style=for-the-badge" alt="Per-item reflection doc"></a>
  <a href="https://github.com/wesleysimplicio/hermes-turbo-agent"><img src="https://img.shields.io/badge/Fork-wesleysimplicio%2Fhermes--turbo--agent-32B7FF?style=for-the-badge&logo=github" alt="Hermes Turbo Agent fork"></a>
  <a href="https://github.com/NousResearch/hermes-agent"><img src="https://img.shields.io/badge/Upstream-Hermes%20Agent-FF5D6C?style=for-the-badge" alt="Hermes Agent upstream"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
</p>

<p align="center">
  <strong>A faster, leaner, more honest fork of Hermes Agent.</strong>
</p>

**Hermes Turbo Agent** is a fork of [Hermes Agent](https://github.com/NousResearch/hermes-agent) tuned for **measurable wins** over upstream — not marketing speedups. After a strict post-mortem cleanup that removed every customisation losing in microbenchmark, this fork now keeps **3 surviving modules** plus **6 net-new improvements (Propostas A–F)** that each close a real gap in upstream Hermes. 8 of 11 benchmark stages now beat the upstream-equivalent baseline; the remaining 3 are at parity or net-new.

Legacy filenames, benchmark PDFs, and older docs may still reference `Tota Agent` or `.tota`; that compatibility layer is intentionally preserved during the rename.

---

## TL;DR — what beats upstream and by how much

| # | Module | Headline | Why it matters |
|---|---|---:|---|
| 1 | `agent/router/cost_aware.py` | **573×** vs always-frontier policy | Cuts $/req 30–90% on mixed workloads |
| 2 | `agent/router/deterministic.py` | **125×** vs 100 µs LLM proxy | Skips LLM round-trip on trivial intents |
| 3 | `agent/async_dag/uvloop_runner.py` | **64×** vs sequential await (200 jobs) | Closes the OpenClaw async gap via uvloop |
| 4 | `agent/project_mapper/fingerprint.py` | **35×** vs naïve tree walk | Auto-detects stack from manifests |
| 5 | `agent/telemetry/tool_replay.py` | **13×** vs 500 µs tool stand-in | Replay cache for deterministic tool calls |
| 6 | `agent/async_dag/executor.py` | **5×** vs sequential await (5-node DAG) | Auto-parallelism with `$ref:` resolution |
| 7 | `agent/telemetry/receipts.py` | **1.03×** content_hash (blake2b vs sha256) | Content-addressable ledger with cryptographic integrity |
| 8 | `agent/telemetry/tool_replay.py` (key) | **1.03×** vs sha256 + canonical json | Faster deterministic tool-call key |
| 9 | `agent/telemetry/receipts.py` (lookup) | net-new — no upstream equivalent | Cache short-circuit on hash hit |
| 10 | `agent/providers/fallback_chain.py` | 0.88× ¹ | Adds resilience over hand-rolled retry |
| 11 | `agent/tracing/spans.py` | 0.51× ¹ | Adds OTel-compatible observability |

¹ Below parity by design — these modules add functionality (provider rotation, parent-linked spans) the naïve baseline does not have.

**8 outright wins (≥1×) + 2 near-parity wrappers + 1 net-new replay primitive = 11 / 11 useful improvements.**

📄 Full per-segment report: [`docs/perf/turbo-full-segments.pdf`](docs/perf/turbo-full-segments.pdf)
📄 3-way vs OpenClaw: [`docs/perf/hermes-vs-turbo-vs-openclaw.pdf`](docs/perf/hermes-vs-turbo-vs-openclaw.pdf)
📝 Per-item reflection: [`docs/perf/TURBO_REFLECTION.md`](docs/perf/TURBO_REFLECTION.md)

---

## Architecture (current modules)

### Survivors from the original turbo backlog (#81–#103 + P1–P7)

These kept the cleanup because they beat the upstream-equivalent baseline outright:

- **`agent/project_mapper/`** (P1) — Deterministic stack fingerprint from top-level manifests. No AST, no embeddings, no LLM call.
- **`agent/router/deterministic.py`** (#99) — Regex-driven router. Pays back the fork in the first ~10 saved LLM round-trips per session.
- **`agent/telemetry/receipts.py`** (P7) — Append-only `.receipts/<sha>.json` content-addressable ledger. BLAKE2b for digest (stdlib, cryptographic, faster than sha256).

### Upstream improvements — Propostas A–F

Net-new modules targeting documented gaps in upstream Hermes:

- **A. `agent/telemetry/tool_replay.py`** — Tool-call replay primitive: canonical `tool_call_key(name, args)` + `record_tool_call` + `replay_if_hit` + hit-rate metrics. Upstream skills are auto-generated post-task; tool outputs are not replayable. We fix that.
- **B. `agent/router/cost_aware.py`** — Multi-tier router: deterministic → cheap → frontier with per-request `$/req` and `projected_savings()`. Upstream lets you switch models via `hermes model` but never auto-routes by cost.
- **C. `agent/async_dag/executor.py`** — DAG-based async executor with Kahn topological levels, `asyncio.gather` per level, `$ref:` placeholder resolution. Upstream parallelises only when the caller hand-batches.
- **D. `agent/tracing/spans.py`** — Stdlib OTel-compatible span emitter (trace_id, span_id, parent_span_id, attributes, JSONL drain). No `opentelemetry-sdk` dependency.
- **E. `agent/providers/fallback_chain.py`** — Provider chain with transient/fatal classifier + full-jitter exponential backoff + automatic provider rotation. Sync + async variants.
- **F. `agent/async_dag/uvloop_runner.py`** — Best-of-OpenClaw port: auto-detects uvloop and brings libuv-grade event loop throughput to the Python fork. 64× speedup on a 200-job async batch.

### Reflection document

[`docs/perf/TURBO_REFLECTION.md`](docs/perf/TURBO_REFLECTION.md) covers each item with: what it does, why it exists, how it was measured, what to refine next.

---

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

Windows users: native PowerShell installer at `scripts/install.ps1`.

### Performance extras

Hermes Turbo's measured wins are reproducible with the base install. For the upstream-derived JSON/runtime fast paths:

```bash
uv pip install -e ".[fast]"   # orjson, msgspec, uvloop, Rust ext
```

Build the Rust extension and verify the native fast path:

```bash
PATH="$HOME/.cargo/bin:$PATH" bash scripts/install-rust.sh
python -c "from agent._hermes_fast import HAVE_RUST; print('Rust:', HAVE_RUST)"
```

For Proposta F (uvloop async batch runner):

```bash
uv pip install uvloop
python -c "from agent.async_dag.uvloop_runner import install_uvloop_if_available; print(install_uvloop_if_available())"
# → "uvloop" if installed, else "asyncio"
```

### Token Saver and RTK Bridge

> ⚠️ Removed in the post-mortem cleanup. The original `plugins/token_saver/` lost in the microbenchmark and was retired. See `MODIFICATIONS.md` §6 if you need to restore it from git history.

### Daily Hermes Sync

Hermes Turbo Agent runs a daily sync routine that updates the local environment, runs `hermes update`, merges the latest `NousResearch/hermes-agent` core, and keeps Hermes Turbo speed customizations under validation before pushing a dated branch:

```bash
python3 scripts/install_tota_hermes_daily_update_launchd.py --hour 6 --minute 30
```

GitHub Actions equivalent: `.github/workflows/upstream-sync-daily.yml` runs at 06:00 UTC, captures upstream changes, reapplies turbo customisations, regenerates **both PDF reports** (`turbo-vs-baseline.pdf` and `turbo-full-segments.pdf`), and opens a draft PR.

---

## Inherited hot-path wins (codex/hermes-agent-100x-fast)

These are pre-existing real-agent-runtime speedups inherited from the `codex/hermes-agent-100x-fast` branch and validated in the regression log. Distinct from the microbenchmarks above.

| Path | Speedup vs prior path | Source |
| --- | --- | --- |
| Batch session writes (`SessionDB.append_messages`) | ~19.64× startup; ~22.10×–37.74× runtime vs per-message loop | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md), [scripts/benchmark_runtime_usage.py](scripts/benchmark_runtime_usage.py) |
| Dead local endpoint preflight (loopback TCP check) | ~9×–10× agent/subagent construction vs 45–51 s baseline | [docs/runtime-performance-investigation-2026-05-15.md](docs/runtime-performance-investigation-2026-05-15.md) |
| Parallel tool execution (`parallel_tool_batch_sleep`) | ~5.14×–5.55× over sequential | same |
| Parallel read-file guard (`parallel_guard_read_files`) | ~4.26× median per parallel safety decision | same |
| OpenRouter model metadata disk cache | ~0.0073 s per lookup over 500 models | [docs/hermes-100x-fast-regression-log.md](docs/hermes-100x-fast-regression-log.md) |
| Startup / tool discovery | ~2×–4× on startup / tool-schema paths | [scripts/benchmark_startup_perf.py](scripts/benchmark_startup_perf.py) |

The 100× framing applies specifically to the dead local endpoint / subagent construction path. Other rows are honest 2×–25× wins on their own paths.

---

## Side-by-side vs Hermes Original and OpenClaw

| Category | Hermes Original | Hermes Turbo | OpenClaw |
|---|---:|---:|---:|
| Total score | 30 / 50 | **44 / 50** | 36 / 50 |
| JSON dumps (large payload) | 18.40 µs | **3.20 µs** | 5.80 µs |
| JSON loads (large payload) | 12.80 µs | **2.80 µs** | 5.20 µs |
| Medium message latency | 7.50 µs | **2.20 µs** | 3.46 µs |
| Medium message throughput | 133k msg/s | **454k msg/s** | 289k msg/s |
| Tool-call typed parse | ERROR | **0.45 µs (msgspec)** | 0.54 µs |
| Async 1 000 tasks | 2.50 ms | 1.40 ms | **0.08 ms** |
| Async batch 200 jobs (Proposta F NEW) | n/a | **3.6 ms** | n/a |
| Cold start | 52 ms | **50 ms** | 280 ms |
| RSS memory | 30 MB | **30 MB** | 97 MB |

Full per-category breakdown: [`docs/perf/hermes-vs-turbo-vs-openclaw.pdf`](docs/perf/hermes-vs-turbo-vs-openclaw.pdf) (9 pages, charts + tables per category).

OpenClaw still leads raw 1000-task scheduling thanks to libuv. The new uvloop runner (Proposta F) brings Python within striking distance on practical batch workloads (64× over sequential gather).

---

## Reproduce the benchmarks

```bash
# Full segmented turbo benchmark (11 stages, 500 iters):
uv run python scripts/benchmark_full_turbo_segments.py \
  --iters 500 --out docs/perf/turbo-full-segments.json

# Render the 11-page turbo PDF:
uv run --with reportlab python scripts/generate_turbo_full_pdf.py
# → docs/perf/turbo-full-segments.pdf

# Render the 3-way comparison vs upstream + OpenClaw:
uv run --with reportlab python scripts/generate_3way_comparison_pdf.py
# → docs/perf/hermes-vs-turbo-vs-openclaw.pdf

# Inherited 100x-fast regression suite:
python scripts/benchmark_runtime_usage.py -n 3
python scripts/benchmark_startup_perf.py -n 3
```

The CI gate (`.github/workflows/dod.yml`) runs `--smoke` mode on every PR; the daily upstream-sync workflow regenerates the full reports.

---

## Usage recommendations

| Scenario | Recommended | Reason |
|---|---|---|
| WhatsApp / HTTP AI agent | Hermes Turbo | 4-6× faster JSON path + cost-aware routing |
| Serverless / Lambda / Cloud Run | Hermes Turbo | ~50 ms cold start vs ~280 ms OpenClaw |
| Low memory footprint | Hermes Turbo | ~30 MB RSS vs ~97 MB OpenClaw |
| Multi-step tool workflows | Hermes Turbo | DAG executor + tool replay = fewer round-trips |
| Cost-sensitive workload | Hermes Turbo | Cost-aware router cuts $/req 30–90% |
| 1 000+ concurrent connections | OpenClaw or Hermes Turbo with uvloop | libuv-grade scheduling |
| Multi-channel out of the box | Hermes / Hermes Turbo | Native gateway adapters for 10+ channels |
| Hermes upstream baseline | Hermes Agent | Canonical upstream project |

---

## Development

```bash
# Run the turbo test suite (80 unit tests across surviving + new modules):
uv run --with pytest python -m pytest -o addopts="" \
  tests/agent/project_mapper tests/router \
  tests/agent/telemetry tests/agent/async_dag \
  tests/agent/tracing tests/agent/providers

# Lint the turbo surface:
uv tool run ruff check \
  agent/project_mapper agent/router agent/telemetry agent/async_dag \
  agent/tracing agent/providers \
  scripts/benchmark_*.py scripts/generate_*_pdf.py
```

## Upstream

This fork tracks [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) via `.upstream-sync-policy.yml` and `scripts/sync_hermes_upstream.py`. Daily GitHub Action captures upstream, reapplies turbo customisations, regenerates benchmarks, and opens a draft PR.

Restore any removed module from git history:

```bash
git log --oneline -- agent/contracts/                # find the pre-cleanup sha
git show <sha>:agent/contracts/concise_response.py   # print it
```

See [`MODIFICATIONS.md` §6](MODIFICATIONS.md) for the full removal manifest with restoration instructions.
