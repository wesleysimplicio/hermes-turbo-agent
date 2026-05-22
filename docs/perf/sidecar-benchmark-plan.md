# Sidecar Benchmark Plan

Companion to `.specs/architecture/ADR-rust-tokio-sidecar.md`. Defines the
methodology that gates whether Option B (Rust+PyO3 sidecar) is prototyped
beyond the ADR. No prototype work begins until this plan runs against the
current `main` and produces numbers stored under `docs/perf/results/`.

## Scope

Three workloads, run in this order. Each must complete on a 4-core / 8 GB
node before promoting to a larger box.

1. **Synthetic 1k-task fan-out** - the original benchmark cited in #84.
   Spawn N async tasks, each does `await asyncio.sleep(jitter)` then a
   shared in-memory increment. N in {100, 500, 1000, 5000}.
2. **Gateway broadcast** - replay a recorded burst of 200 inbound messages
   across 5 platforms with platform-specific rate limits enforced.
3. **Retry storm** - inject 10% failures upstream and measure scheduler
   behavior under exponential backoff with jitter.

## Variants

Run each workload against three builds, same hardware, same kernel:

- `A` - current `main` with `uvloop` enabled.
- `B` - prototype branch with `TOTA_FAST_GATEWAY=1` (PyO3 sidecar).
- `C` - sibling experiment with the standalone Tokio sidecar over Unix
  socket gRPC. Optional; run only if B clears its gate.

## Metrics

Capture for each `(workload, variant)` cell. Five runs, drop high+low,
report median + IQR.

| Metric                  | Unit       | How                                          |
| ----------------------- | ---------- | -------------------------------------------- |
| p50 task latency        | ms         | per-task wall clock from spawn to completion |
| p99 task latency        | ms         | same                                         |
| p99.9 task latency      | ms         | same                                         |
| Throughput              | tasks/s    | total tasks / wall time                      |
| CPU utilization         | % per core | `psutil` per process, 100ms samples          |
| RSS peak                | MB         | `psutil` peak across run                     |
| GC pause max (Python)   | ms         | `gc.callbacks` instrumentation               |
| FFI overhead (B only)   | us         | tracing span around PyO3 boundary            |
| IPC overhead (C only)   | us         | tracing span around gRPC call                |
| Crash / panic count     | int        | must be 0; non-zero fails the gate           |

## Correctness gate (must pass before perf is even considered)

A parity test replays the gateway broadcast workload through both `A` and
`B`, captures every outbound message in order with timestamp truncated to
1ms, and asserts identical message bodies and identical send order per
platform. Any divergence fails the gate.

## Success criteria

Option B is approved for prototype if **all** of the following hold:

- p99 task latency on workload 1 (N=1000): `B` is at least **30% lower**
  than `A`.
- p99 task latency on workload 2: `B` is at least **20% lower** than `A`.
- Throughput on workload 1 (N=1000): `B` is at least **2x** `A`.
- Correctness gate passes on workloads 1, 2, and 3.
- No panic, no segfault, no Python-side `RuntimeError` from the bridge.
- RSS peak: `B` <= 1.5x `A`.
- FFI overhead median <= 5us per call.

Option C is greenlit only if B fails *and* a customer use case demands
horizontal scaling.

## Tooling

- Bench harness: `pytest-benchmark` for in-process; `wrk2`-style custom
  driver for the broadcast workload.
- Metric capture: `pytest-benchmark` JSON + custom CSV writer; results
  land in `docs/perf/results/<date>/` and are checked into the repo.
- Tracing: `opentelemetry-sdk` with a no-op exporter in default builds.

## Out of scope

- Multi-host scale-out (covered by future ADR for Option C).
- Persistent queue backpressure under disk-full conditions.
- Cold-start latency of the sidecar (measured separately if B ships).

## Open questions

- Is `pyo3-async-runtimes` stable enough on Python 3.13t (free-threading)?
- Does `manylinux2014` still cover our target distros, or do we need
  `manylinux_2_28`?
- How do we expose the new metrics to the existing observability plugin
  without changing its schema?