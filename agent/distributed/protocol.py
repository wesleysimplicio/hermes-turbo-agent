"""Wire-protocol dataclasses for the distributed node host.

These are **types only**. No transport, no serialization helpers, no
behavior beyond what `@dataclass(slots=True, frozen=True)` provides.
See `docs/adr/0006-distributed-node-host.md` for the contract and
`docs/distributed/overview.md` for the operator-facing summary.

The shapes here are designed to be msgspec-compatible: every field uses
primitives or other dataclasses, no `Any`, no `dict[str, object]` at
the top level. When the gateway lands we add a thin
`msgspec.Struct`-based encoder pair alongside these definitions rather
than replacing them, so static consumers keep working.

Protocol version is tracked via `PROTOCOL_VERSION` below. Any field
addition or removal is a protocol-version bump and lands in a follow-up
ADR.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

PROTOCOL_VERSION: int = 1
"""Wire-protocol version. Bumped on any breaking change to the
dataclasses in this module. Nodes and gateways exchange this in
`NodeRegister` and refuse mismatched majors."""


class Surface(str, Enum):
    """Physical surface a node runs on."""

    DESKTOP = "desktop"
    CAR = "car"
    MOBILE = "mobile"
    BROWSER_POD = "browser_pod"
    HEADLESS = "headless"


class Lane(str, Enum):
    """Execution lane (yool spec section 6). Drives queue selection."""

    FAST = "fast"
    SLOW = "slow"
    BACKGROUND = "background"


class Authority(str, Enum):
    """Capability authority level (yool spec section 5)."""

    DEV = "dev"
    OPS = "ops"
    REVIEW = "review"
    AUDIT = "audit"


@dataclass(slots=True, frozen=True)
class AgentTerms:
    """Mandatory guardrails declared per capability.

    Per the yool spec (sections 11.1 and 11.2) `cpu_quota_pct` and
    `disk_quota_mb` are mandatory. A capability that omits them is
    rejected at `NodeRegister`. Victor Genaro's review: "precisa de
    guardrail pra nao fritar o processador. Voce precisa de garbage
    collector tambem pra nao encher 100% do disco."
    """

    cpu_quota_pct: int
    disk_quota_mb: int
    timeout_s: int = 30


@dataclass(slots=True, frozen=True)
class Capability:
    """One typed capability a node exposes.

    `yool_id` follows `capability.<surface>.<verb>` and is used as the
    HAMT key in the registry (ADR-0006 section 4).
    """

    yool_id: str
    authority: Authority
    lane: Lane
    agent_terms: AgentTerms


@dataclass(slots=True, frozen=True)
class NodeRegister:
    """Sent node -> gateway on connect and on every capability change.

    The gateway rejects the message if `protocol_version` major does
    not match `PROTOCOL_VERSION`, if `auth_token` is unknown, or if any
    capability omits mandatory `agent_terms` fields.
    """

    node_id: str
    surface: Surface
    capabilities: tuple[Capability, ...]
    auth_token: str
    protocol_version: int = PROTOCOL_VERSION


@dataclass(slots=True, frozen=True)
class TaskDispatch:
    """Sent control plane -> gateway -> node.

    `payload` is opaque to the gateway; only the destination node
    parses it. `approval_token` is required for sensitive capabilities
    (see ADR-0006 section 3) and is scoped to one capability + one node
    + one payload hash. Secrets MUST NOT appear inline; reference them
    by alias resolved against the node's local keystore.
    """

    task_id: str
    capability: str  # yool_id
    payload: bytes
    deadline_s: float
    idempotency_key: str
    approval_token: str | None = None


TaskStatus = Literal["ok", "error", "timeout", "denied"]


@dataclass(slots=True, frozen=True)
class TaskResult:
    """Sent node -> gateway -> control plane.

    `result_payload` is opaque to the gateway. `error` is populated
    only when `status != "ok"`.
    """

    task_id: str
    node_id: str
    status: TaskStatus
    result_payload: bytes
    elapsed_ms: int
    error: str | None = None


@dataclass(slots=True, frozen=True)
class HealthPing:
    """Bidirectional liveness + load signal.

    Missing 3 consecutive pings marks the node degraded; missing 6
    evicts it (ADR-0006 section 5). Quotas are reported as percentages
    of the limits declared in `Capability.agent_terms` so the gateway
    can apply backpressure without knowing the absolute machine size.
    """

    node_id: str
    ts: float
    inflight_count: int
    cpu_pct: float
    mem_pct: float
    disk_pct: float


__all__ = [
    "PROTOCOL_VERSION",
    "AgentTerms",
    "Authority",
    "Capability",
    "HealthPing",
    "Lane",
    "NodeRegister",
    "Surface",
    "TaskDispatch",
    "TaskResult",
    "TaskStatus",
]
