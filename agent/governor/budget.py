"""Token budget governor for autonomous loops.

Records spend at each step and raises ``BudgetExceeded`` once any configured
limit is hit. Pure stdlib, no external deps. Designed for ``/goal`` and
Ralph-style loops that would otherwise silently burn context.

Usage::

    cfg = BudgetConfig(max_tokens_per_loop=100_000, max_cost_usd=2.0, max_iterations=50)
    gov = BudgetGovernor(cfg)
    for step in loop():
        gov.record_step(tokens=step.tokens, cost_usd=step.cost)
        # raises BudgetExceeded when any axis hits 100%
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional


class BudgetExceeded(RuntimeError):
    """Raised when at least one budget axis hits its hard limit."""

    def __init__(self, axis: str, used: float, limit: float) -> None:
        super().__init__(f"budget exceeded on {axis}: used={used} limit={limit}")
        self.axis = axis
        self.used = used
        self.limit = limit


@dataclass(frozen=True)
class BudgetConfig:
    """Budget knobs for a single autonomous loop.

    A limit of ``None`` means "do not enforce this axis".
    """

    max_tokens_per_loop: Optional[int] = None
    max_cost_usd: Optional[float] = None
    max_iterations: Optional[int] = None


@dataclass(frozen=True)
class BudgetSnapshot:
    """Immutable view of current spend on each axis."""

    tokens: int
    cost_usd: float
    iterations: int

    def ratio(self, cfg: BudgetConfig) -> float:
        """Highest used/limit ratio across axes (0.0 if no limits set)."""
        ratios: List[float] = []
        if cfg.max_tokens_per_loop:
            ratios.append(self.tokens / cfg.max_tokens_per_loop)
        if cfg.max_cost_usd:
            ratios.append(self.cost_usd / cfg.max_cost_usd)
        if cfg.max_iterations:
            ratios.append(self.iterations / cfg.max_iterations)
        return max(ratios) if ratios else 0.0


@dataclass
class BudgetGovernor:
    """Records spend and enforces a ``BudgetConfig``.

    Optional ``on_warn`` callback fires once per axis when the warn threshold
    is crossed; useful to flip compression mode before the hard stop.
    """

    config: BudgetConfig
    warn_ratio: float = 0.70
    on_warn: Optional[Callable[[str, BudgetSnapshot], None]] = None
    _tokens: int = field(default=0, init=False)
    _cost_usd: float = field(default=0.0, init=False)
    _iterations: int = field(default=0, init=False)
    _warned: set = field(default_factory=set, init=False)

    def snapshot(self) -> BudgetSnapshot:
        return BudgetSnapshot(
            tokens=self._tokens,
            cost_usd=self._cost_usd,
            iterations=self._iterations,
        )

    def record_step(self, *, tokens: int = 0, cost_usd: float = 0.0) -> BudgetSnapshot:
        """Add one iteration of spend, fire warnings, raise on overflow."""
        if tokens < 0 or cost_usd < 0:
            raise ValueError("tokens and cost_usd must be non-negative")
        self._tokens += tokens
        self._cost_usd += cost_usd
        self._iterations += 1
        snap = self.snapshot()
        self._emit_warnings(snap)
        self._enforce(snap)
        return snap

    def _emit_warnings(self, snap: BudgetSnapshot) -> None:
        if self.on_warn is None:
            return
        for axis, used, limit in self._axes():
            if limit is None or axis in self._warned:
                continue
            if used / limit >= self.warn_ratio:
                self._warned.add(axis)
                self.on_warn(axis, snap)

    def _enforce(self, snap: BudgetSnapshot) -> None:
        for axis, used, limit in self._axes():
            if limit is not None and used >= limit:
                raise BudgetExceeded(axis=axis, used=used, limit=limit)

    def _axes(self):
        yield "tokens", self._tokens, self.config.max_tokens_per_loop
        yield "cost_usd", self._cost_usd, self.config.max_cost_usd
        yield "iterations", self._iterations, self.config.max_iterations
