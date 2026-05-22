"""Token budget governor for autonomous loops.

Public surface:
    - BudgetConfig: budget knobs (tokens, cost, iterations).
    - BudgetGovernor: records spend and enforces limits.
    - BudgetExceeded: raised when any limit is hit.
    - EscalationPolicy / WarnAt70HardStopAt100: warn/stop thresholds.
"""

from .budget import BudgetConfig, BudgetExceeded, BudgetGovernor, BudgetSnapshot
from .policies import (
    EscalationLevel,
    EscalationPolicy,
    WarnAt70HardStopAt100,
)

__all__ = [
    "BudgetConfig",
    "BudgetExceeded",
    "BudgetGovernor",
    "BudgetSnapshot",
    "EscalationLevel",
    "EscalationPolicy",
    "WarnAt70HardStopAt100",
]
