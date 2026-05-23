# ADR: Optional Rust/Tokio Sidecar for High-Concurrency Gateway Paths

- Status: Proposed
- Date: 2026-05-21
- Refs: #84
- Supersedes: -

## Context

The Hermes Turbo Agent gateway aggregates traffic from 20+ messaging platforms
(Telegram, WhatsApp, Discord, Slack, Matrix, Signal, webhook, api_server, ...).
Most production workloads are I/O-bound and well served by Python `asyncio`
plus `uvloop`. However, a synthetic 1,000-task scheduler benchmark still shows
Node/libuv and Rust/Tokio outperforming pure Python for fan-out, timer-heavy,
and cross-platform broadcast workloads. Issue #84 asks whether an **optional,
disabled-by-default** sidecar can close that gap without complicating the
default CLI experience.

This ADR compares three credible paths and recommends one.

## Decision drivers

- p50/p99 latency under sustained 1k+ concurrent tasks
- Throughput ceiling (tasks/s) on a single 4-core gateway node
- Build/packaging cost (wheels, cross-compile, supply chain)
- Operational cost (process supervision, logs, health, upgrade)
- Blast radius if the sidecar fails (must degrade to pure Python)
- Maintenance surface (people who can debug it)

## Options

### Option A - Pure Python `asyncio` + `uvloop` (status quo plus tuning)

Keep everything in-process. Tune: `uvloop.install()`, bounded
`asyncio.Semaphore` per platform, replace `asyncio.gather` with
`TaskGroup`, batch DB writes, push hot loops into the existing
`hermes_fast` Rust extension via PyO3.

- Pros: zero new process, single deploy artifact, debuggable with stdlib
  tracing, packaging unchanged, contributors already fluent.
- Cons: GIL still bounds CPU-bound coalescing; scheduler still loses the
  synthetic 1k-task benchmark by roughly 30-50% vs Tokio; tail latency
  spikes during GC pauses remain.

### Option B - Rust + PyO3 sidecar in-process (`hermes_fast_gateway`)

Extend the existing `hermes_fast` Rust extension with a Tokio runtime that
owns the hot loop (fan-out, timers, retry queues, rate limiters). Python
keeps platform adapters and business logic; Rust exposes async functions via
PyO3 + `pyo3-async-runtimes`.

- Pros: no second process to supervise; shares logger/config; can be a/b
  toggled by feature flag; reuses Hermes Turbo's existing Rust build pipeline; FFI
  overhead is sub-microsecond.
- Cons: PyO3 + Tokio bridging is non-trivial (GIL handoff, cancellation
  semantics); a Rust panic still kills the Python process unless wrapped in
  `catch_unwind`; manylinux/musllinux wheel matrix expands; debugging
  segfaults requires `gdb`/`lldb`, not every contributor has the toolchain.

### Option C - Standalone Tokio service with gRPC bridge (`tota-gateway-rs`)

Ship a separate Rust binary speaking gRPC (or Unix-socket length-prefixed
protobuf). Python gateway becomes a thin proxy when the env var
`TOTA_GATEWAY_SIDECAR=1` is set; otherwise it stays in-process.

- Pros: full process isolation (panic != user-visible crash); independent
  release cycle; can be deployed on a different host for horizontal scale;
  benchmark gains land closest to theoretical max because Python's GIL is
  out of the hot path entirely.
- Cons: two binaries to package, supervise (systemd unit, log rotation,
  health probe), and upgrade in lockstep on schema change; gRPC adds
  ~10-30us per message; CLI users now have a second daemon to install or
  Docker image gets a multi-stage build; debugging crosses a process
  boundary.

## Comparison

| Dimension              | A (pure Python)    | B (PyO3 sidecar)   | C (gRPC sidecar)   |
| ---------------------- | ------------------ | ------------------ | ------------------ |
| Expected p50 @ 1k task | baseline           | -30% to -50%       | -50% to -65%       |
| Expected p99 @ 1k task | baseline           | -20% to -40%       | -40% to -55%       |
| Throughput ceiling     | baseline           | 2-3x               | 3-5x               |
| Build complexity       | none               | medium (wheels)    | high (2 artifacts) |
| Ops complexity         | none               | low                | medium-high        |
| Blast radius isolation | n/a                | weak (in-process)  | strong (process)   |
| Optional + off default | trivial            | feature flag       | env-var gated      |
| CLI UX impact          | none               | none               | one extra daemon   |
| Contributor reach      | broad              | narrow (Rust)      | narrow (Rust+gRPC) |

Numbers are directional estimates from published Tokio/uvloop benchmarks and
must be replaced by repo-local numbers from `docs/perf/sidecar-benchmark-plan.md`
before any prototype merges.

## Decision

**Recommend Option B (PyO3 sidecar) as the prototype path, contingent on the
benchmark plan in `docs/perf/sidecar-benchmark-plan.md` producing a >=30%
p99 reduction on the gateway hot loops listed there.**

Rationale: B keeps the single-binary CLI promise that ships Hermes Turbo today,
reuses the Rust toolchain Hermes already maintains for `hermes_fast`, and
closes most of the gap without a second daemon. C remains an explicit
follow-up if and only if B fails the panic-isolation gate or if a customer
emerges who needs horizontal sidecar scaling.

A stays the baseline and shipping default. The sidecar is loaded only when
`TOTA_FAST_GATEWAY=1` is set; absent the flag, behavior must be
byte-identical to today.

## Consequences

- New optional dependency: `pyo3-async-runtimes` and a Tokio-based crate
  inside the existing `hermes_fast` workspace.
- Wheel matrix gains one Rust feature flag; CI must build both with and
  without it.
- A correctness gate (parity test suite) must run both code paths against
  the same input and assert byte-identical outputs before any release with
  the flag flipped to default-on.
- If the benchmark fails the >=30% p99 gate, the prototype is discarded
  and this ADR is superseded by one that locks in Option A indefinitely.

## Alternatives considered

- Node/libuv sidecar: rejected - adds a third language runtime and Node's
  GC pause profile is not obviously better than Python's for this workload.
- `multiprocessing` + shared memory: rejected - IPC cost dwarfs the
  scheduler win; we measured this in #62.

## Follow-up

- Implement `docs/perf/sidecar-benchmark-plan.md` first.
- Open a prototype issue gated on benchmark results.
- If approved, write ADR for Option C as the horizontal-scale path.