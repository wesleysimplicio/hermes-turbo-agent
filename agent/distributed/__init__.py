"""Distributed node host package.

See `docs/adr/0006-distributed-node-host.md` for the architecture
and `docs/distributed/overview.md` for the operator-facing summary.

This module currently exposes only the wire-protocol dataclasses
(`agent.distributed.protocol`). Gateway and node-runtime implementations
land in follow-up PRs per the ADR prototype plan.
"""

from agent.distributed.protocol import (
    HealthPing,
    NodeRegister,
    TaskDispatch,
    TaskResult,
)

__all__ = [
    "HealthPing",
    "NodeRegister",
    "TaskDispatch",
    "TaskResult",
]
