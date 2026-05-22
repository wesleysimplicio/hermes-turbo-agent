# Distributed node host — overview

Operator-facing summary of the distributed node host. Architecture and trade-offs live in [`docs/adr/0006-distributed-node-host.md`](../adr/0006-distributed-node-host.md); wire types live in [`agent/distributed/protocol.py`](../../agent/distributed/protocol.py).

## What it is

Hermes Turbo splits work between a **control plane** (the agent loop, prompt assembly, history, skills) and a **node plane** (the surfaces that touch real hardware — desktop, car head-unit, mobile, headless browser pod). A **gateway** sits in the middle and gives the control plane one connection no matter how many nodes are paired.

```
+-----------------+        +-----------+        +-----------+
|  control plane  | <----> |  gateway  | <----> |  node A   |
|  (agent loop)   |        |           | <----> |  node B   |
+-----------------+        +-----------+ <----> |  node C   |
                                                +-----------+
```

The agent loop never imports node code and never spawns a subprocess. It addresses a capability by yool id (`capability.<surface>.<verb>`) and the gateway routes the dispatch to a node that owns it.

## Roles

- **Control plane.** Runs the model-facing loop. Holds conversation state, skills, the prompt-cache stable prefix (see ADR-0005). Emits `TaskDispatch` envelopes; consumes `TaskResult`.
- **Gateway.** Multiplexes nodes. Owns the capability registry (a HAMT keyed on `yool_id`), the pairing table, the in-flight task ledger (SQLite + WAL), and the approval policy.
- **Node.** Lives on the surface that owns a capability. Registers its capability set on connect via `NodeRegister`, executes dispatched tasks, returns `TaskResult`. Stateless across tasks except for capability-local resources (open browser tabs, screen-capture pipes).

## Wire types

Four message types, defined in `agent/distributed/protocol.py`:

| Type | Direction | Purpose |
|------|-----------|---------|
| `NodeRegister` | node -> gateway | Declare identity, surface, capabilities, auth token, protocol version. |
| `TaskDispatch` | control -> gateway -> node | Carry one task: capability, payload, approval token, deadline, idempotency key. |
| `TaskResult` | node -> gateway -> control | Return outcome: `ok|error|timeout|denied`, payload, elapsed ms. |
| `HealthPing` | bidirectional | Liveness + load signal. Drives degraded/evicted state machine. |

All four are `@dataclass(slots=True, frozen=True)` and msgspec-friendly. Protocol version is tracked in `PROTOCOL_VERSION`; a major mismatch is rejected at registration.

## Auth + approval

Three independent layers. All three must pass:

1. **Pairing.** First contact uses an out-of-band code (short numeric, QR fallback on the car HUD). On success the node receives a long-lived, revocable `auth_token` scoped to that gateway.
2. **Authn.** Every `NodeRegister` and `TaskDispatch` carries `auth_token`. Unknown token = reject.
3. **Approval.** Sensitive capabilities (`system.run`, `screen.capture`, `location.read`, anything writing outside a sandbox) require a per-task `approval_token` minted by the human-in-the-loop UI. The agent loop cannot mint approval tokens itself. Tokens are scoped to one capability + one node + one payload hash and expire in seconds.

Secrets never travel in `TaskDispatch.payload`. The dispatch references credentials by alias; the node resolves the alias against its local keystore.

## Guardrails (mandatory)

Every registered capability declares `agent_terms` with `cpu_quota_pct` and `disk_quota_mb` (yool spec sections 11.1 and 11.2). Capabilities without these fields are rejected at `NodeRegister`. This is the same guardrail contract the rest of the agent uses; the node host does not get to opt out.

## Failover

- **Health.** Missing 3 consecutive `HealthPing`s (default 9s) marks a node degraded; missing 6 evicts it.
- **In-flight tasks** on an evicted node fan out to other nodes with the same capability if any exist. Otherwise the control plane sees `TaskResult{status="timeout"}` and decides whether to retry.
- **Gateway** persists pairing + in-flight ledger to SQLite (WAL). When configured with a follower, leader/follower replication replays the ledger on failover.
- **Control plane state never lives on a node**, so any node crash is recoverable. Capability-local resources (browser tabs, screen pipes) reconcile on reconnect.

## What is NOT in this iteration

- No real network transport yet — only the type contract.
- No gateway implementation; no node runtime. Both land in follow-up PRs per the ADR prototype plan.
- No multi-tenant gateway. One gateway = one operator.
- Latency-critical local hooks (IME, key remapping) stay in-process and are explicitly out of scope.

## Pointers

- ADR: `docs/adr/0006-distributed-node-host.md`
- Types: `agent/distributed/protocol.py`
- Yool / HAMT spec: https://github.com/wesleysimplicio/yool-tuple-hamt
- Tracking issue: https://github.com/wesleysimplicio/hermes-turbo-agent/issues/97
