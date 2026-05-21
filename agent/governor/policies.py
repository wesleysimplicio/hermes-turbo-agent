"""Escalation policies layered on top of ``BudgetGovernor``.

A policy reads a ``BudgetSnapshot`` + ``BudgetConfig`` and returns the
escalation level the loop should react to:

    OK    -- under 70%, business as usual.
    WARN  -- at/over 70%, switch to compressed/focused mode.
    STOP  -- at/over 100%, hard stop (``BudgetGovernor`` will also raise).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from .budget import BudgetConfig, BudgetSnapshot


class EscalationLevel(str, Enum):
    OK = "ok"
    WARN = "warn"
    STOP = "stop"


class EscalationPolicy(Protocol):
    """Reads spend, returns the recommended level."""

    def evaluate(
        self, snapshot: BudgetSnapshot, config: BudgetConfig
    ) -> EscalationLevel:  # pragma: no cover - protocol
        ...


@dataclass(frozen=True)
class WarnAt70HardStopAt100:
    """Default escalation: warn at 70%, hard stop at 100% of any axis."""

    warn_ratio: float = 0.70
    stop_ratio: float = 1.00

    def evaluate(
        self, snapshot: BudgetSnapshot, config: BudgetConfig
    ) -> EscalationLevel:
        ratio = snapshot.ratio(config)
        if ratio >= self.stop_ratio:
            return EscalationLevel.STOP
        if ratio >= self.warn_ratio:
            return EscalationLevel.WARN
        return EscalationLevel.OK
