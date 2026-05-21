# ADR-0006: Distributed node host architecture

**Status:** Proposed.
**Date:** 2026-05-21.
**Owner:** @wesleysimplicio.
**Related:** GitHub issue #97. Builds on ADR-0005 (prompt-cache stable prefix) for control-plane prompt assembly, and ADR-0004 (perf budgets) for node-side execution budgets.

## Context

OpenClaw ships a Gateway + Nodes architecture that lets a single agent loop drive `system.run`, browser automation, screen/location capture, notifications, and platform-specific commands on **remote** surfaces (desktop, car, mobile) while keeping the model-facing loop isolated from device IO. Hermes Turbo today executes everything in-process: tools that touch local hardware (browser, OS shell, camera, GPS, notifications) only work where the agent process runs. That blocks the desktop + car + remote-browser surfaces in `PERFORMANCE_ROADMAP.md`.

Issue #97 asks for parity: define a Gateway/daemon/client/node split, a typed capability registry, pairing/auth/approval semantics, and an ADR + prototype plan **before** any production code lands.

## Decision

Adopt a two-plane architecture with a typed RPC contract and capability addressing.

### 1. Plane split

- **Control plane** — owns the model-facing agent loop, prompt assembly, history, skills, and policy. Single process per session. Never executes a node tool directly; emits typed `TaskDispatch` envelopes.
- **Node plane** — one or more *nodes*, each registered with a typed capability set (`system.run`, `browser.*`, `screen.capture`, `location.read`, `notifications.send`, `platform.<surface>.*`). A node runs on the surface that owns the capability (desktop, car head-unit, phone, headless browser pod).
- **Gateway** — the only thing the control plane talks to. Multiplexes many nodes, persists pairing state, enforces approval, and exposes the same `dispatch / result / health` surface to the agent loop regardless of node count.

A node is **never** loaded into the agent's Python module graph. The agent loop cannot import node code; it can only address a capability over the wire. This guarantees the existing isolation property (no `subprocess.Popen` from the model loop) is preserved as we scale to N surfaces.

### 2. RPC contract

Four message types form the wire protocol. Types live in `agent/distributed/protocol.py` (this PR ships dataclass skeletons; impl deferred):

- `NodeRegister` — node to gateway. Declares `node_id`, `surface`, `capabilities[]`, `auth_token`, `protocol_version`. Sent on connect + on every capability change.
- `TaskDispatch` — control plane to gateway to node. Carries `task_id`, `capability` (yool id, see section 4), `payload`, `approval_token`, `deadline_s`, `idempotency_key`.
- `TaskResult` — node to gateway to control plane. Carries `task_id`, `status` (`ok|error|timeout|denied`), `result_payload`, `error`, `elapsed_ms`, `node_id`.
- `HealthPing` — bidirectional. Carries `node_id`, `ts`, `inflight_count`, `cpu_pct`, `mem_pct`, `disk_pct`. Drives failover (section 5).

Wire format: msgspec-encoded JSON over a single long-lived bidirectional stream (gRPC-style, but transport is HTTP/2 + JSON for now — keeps debugging trivial and aligns with `_fastjson`). Transport-level changes do not require ADR revisions; payload schema changes do.

### 3. Auth + pairing + approval

Three layers, all required:

1. **Pairing** — first contact between a node and the gateway uses an out-of-band pairing code (short-lived, single-use, displayed on the gateway operator's screen / car HUD). On success the node receives a long-lived `auth_token` scoped to that gateway. Tokens are revocable.
2. **Authn** — every `NodeRegister` / `TaskDispatch` carries `auth_token`. Gateway rejects unknown tokens. Nodes reject dispatches from gateways they did not pair with.
3. **Approval** — sensitive capabilities (`system.run`, `screen.capture`, `location.read`, anything writing files outside a sandbox) require a per-task `approval_token` minted by the human-in-the-loop UI on the controlling surface. Approval tokens are scoped to one capability + one node + one payload-hash and expire in seconds. The agent loop **cannot** mint approval tokens itself.

Secrets never appear in `TaskDispatch.payload`. Credentials live in the node's local keystore; the dispatch references them by alias.

### 4. Capability addressing (yool / tuple / HAMT)

Capabilities are addressed using the yool/tuple/HAMT scheme adopted in this repo (spec at https://github.com/wesleysimplicio/yool-tuple-hamt). Each capability declares:

```
yool_id: capability.<surface>.<verb>     # e.g. capability.desktop.system.run
authority: dev | ops | review | audit
lane: fast | slow | background
agent_terms:
    cpu_quota_pct: <int, MANDATORY>      # spec section 11.1
    disk_quota_mb: <int, MANDATORY>      # spec section 11.2
    timeout_s: <int>
```

The capability registry is a HAMT keyed on `yool_id`; lookup is O(log32 N) and immutable per-version, so the agent loop can take a snapshot at task start and the registry can update concurrently without races. Guardrails (`cpu_quota_pct`, `disk_quota_mb`) are **mandatory** per the yool spec — a node that registers a capability without them is rejected at `NodeRegister`.

### 5. Failover + state sync

State is split by ownership:

- **Control plane state** (conversation history, skills, prompt cache anchors) lives only in the control plane. Nodes are stateless across tasks except for capability-local resources (open browser tabs, mounted screen capture pipes). Crash of one node never loses agent state.
- **Gateway state** (pairing table, in-flight task ledger, capability registry snapshot) is persisted to a local SQLite file with WAL and replicated to a sibling gateway when configured. Failover is leader/follower; the follower replays the in-flight ledger and re-routes orphaned dispatches once it observes a leader-down signal for `>health_timeout_s`.
- **Node-local resources** are reconciled on reconnect: the gateway sends `NodeRegister` ACK with the list of in-flight `task_id`s it believes the node owns; the node replies with the actual set and the gateway issues `TaskResult{status=error, error="orphaned"}` for the delta.

`HealthPing` drives liveness: missing 3 consecutive pings (default 9s wall) -> node marked degraded; missing 6 -> evicted; in-flight tasks fan out to other nodes with the same capability if any, otherwise return `status=timeout`.

## Consequences

- **Positive.** Parity with OpenClaw on remote surfaces. Agent loop stays isolated from device IO. Failure of one surface (car head-unit goes offline) does not crash the agent. Auth is explicit and revocable. Capability addressing is typed end-to-end.
- **Negative.** Adds a wire protocol the team must version and debug. Latency floor for a dispatched task is bounded by network RTT + queue depth, not local syscalls — so latency-critical capabilities (key remapping, IME hooks) stay in-process and are explicitly out of scope for the node plane. Pairing UX must work on surfaces without keyboards (car HUD) — addressed by short numeric pairing codes + QR fallback.
- **Cost.** Gateway is a new operational component. We will bundle it in the existing `hermes` CLI as `hermes gateway run` rather than ship a separate package.

## Out of scope (this ADR)

- Concrete transport tuning (HTTP/2 vs QUIC vs WebSocket) — chosen during prototype, not ADR-level.
- Specific node implementations (browser pod, desktop daemon, car runtime).
- UI/UX of the approval dialog.
- Multi-tenant gateway (one gateway = one operator for now).

## Alternatives considered

1. **In-process tool plugins with subprocess fan-out.** Rejected: violates the isolation property and does not address remote surfaces.
2. **MCP-only.** MCP works for tool surface but does not model pairing, approval, or failover across long-lived remote nodes. MCP tools continue to be exposed where they fit; the node host is the layer underneath.
3. **OpenClaw Gateway as-is, wrapped.** Rejected: license + dependency footprint, and the typed capability model in OpenClaw differs from yool/HAMT enough that a thin wrapper would leak both abstractions.

## Prototype plan

1. Land this ADR + protocol skeleton (this PR).
2. Prototype gateway in `agent/distributed/gateway.py` with SQLite ledger and a single in-process loopback node. No real network yet.
3. Add `agent/distributed/node_runtime.py` with one real capability: `system.run` on the local desktop. Pairing via terminal.
4. Add E2E test that dispatches `system.run` from the agent loop, observes `TaskResult`, and asserts isolation (agent process never `Popen`s anything).
5. Iterate: browser node, screen capture node, car runtime.

Production rollout is gated on a separate ADR ("ADR-0007: Node host GA criteria") once steps 2–4 are green.
