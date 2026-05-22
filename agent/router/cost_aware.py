"""Cost-aware multi-tier router. Improves what upstream Hermes does.

Upstream Hermes lets you swap models via ``hermes model`` but does NOT track
$/req nor auto-route by cost. Every prompt — trivial or frontier-class —
hits whatever model is selected. That is real money wasted on simple intents.

This module layers cost-awareness on top of the deterministic regex router
that survived the post-mortem cleanup:

    deterministic (free, ~1 µs)
        → on miss, try the cheap tier (e.g. Haiku, $0.25/$1.25 per 1M tok)
            → on low-confidence, escalate to the frontier tier (Opus, $15/$75)

Per-request cost is accumulated in ``CostMetrics`` so the operator can see
exactly where the money went and tune the tier table or confidence threshold.

Stdlib-only. The LLM callables are passed in; this module owns the routing
policy, not the SDK glue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

from .deterministic import DeterministicRouter, RouteDecision


@dataclass(frozen=True)
class TierCost:
    """Provider-side pricing for one model tier (USD per 1M tokens).

    Defaults loosely approximate the Anthropic public price list as of 2026
    — adjust per your contract.
    """

    name: str
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    avg_input_tokens: int = 400
    avg_output_tokens: int = 200

    def avg_usd(self) -> float:
        """Expected cost of one round-trip at the configured avg shape."""

        return (
            self.input_usd_per_mtok * self.avg_input_tokens
            + self.output_usd_per_mtok * self.avg_output_tokens
        ) / 1_000_000


# Reasonable defaults; override at construction time when calling.
DEFAULT_CHEAP_TIER = TierCost(
    name="haiku", input_usd_per_mtok=0.25, output_usd_per_mtok=1.25,
)
DEFAULT_FRONTIER_TIER = TierCost(
    name="opus", input_usd_per_mtok=15.0, output_usd_per_mtok=75.0,
)


@dataclass
class TierResult:
    """Whatever the model returned plus the (input, output) token count."""

    decision: RouteDecision
    input_tokens: int = 0
    output_tokens: int = 0


TierCallable = Callable[[str], TierResult]


@dataclass
class CostMetrics:
    deterministic_hits: int = 0
    cheap_hits: int = 0
    frontier_hits: int = 0
    empty_or_invalid: int = 0
    cheap_usd: float = 0.0
    frontier_usd: float = 0.0
    cheap_tokens_in: int = 0
    cheap_tokens_out: int = 0
    frontier_tokens_in: int = 0
    frontier_tokens_out: int = 0

    @property
    def total_requests(self) -> int:
        return (
            self.deterministic_hits
            + self.cheap_hits
            + self.frontier_hits
            + self.empty_or_invalid
        )

    @property
    def total_usd(self) -> float:
        return self.cheap_usd + self.frontier_usd

    @property
    def avoided_frontier_calls(self) -> int:
        return self.deterministic_hits + self.cheap_hits

    @property
    def deterministic_ratio(self) -> float:
        n = self.total_requests
        return self.deterministic_hits / n if n else 0.0

    def as_dict(self) -> dict[str, object]:
        return {
            "deterministic_hits": self.deterministic_hits,
            "cheap_hits": self.cheap_hits,
            "frontier_hits": self.frontier_hits,
            "empty_or_invalid": self.empty_or_invalid,
            "total_requests": self.total_requests,
            "deterministic_ratio": round(self.deterministic_ratio, 4),
            "avoided_frontier_calls": self.avoided_frontier_calls,
            "cheap_usd": round(self.cheap_usd, 6),
            "frontier_usd": round(self.frontier_usd, 6),
            "total_usd": round(self.total_usd, 6),
            "cheap_tokens_in": self.cheap_tokens_in,
            "cheap_tokens_out": self.cheap_tokens_out,
            "frontier_tokens_in": self.frontier_tokens_in,
            "frontier_tokens_out": self.frontier_tokens_out,
        }


@dataclass
class CostAwareRouter:
    """Multi-tier router with explicit cost accounting.

    Decision flow:
      1. Run the deterministic router. If it matches, return immediately —
         cost = 0.
      2. On miss, invoke the cheap tier. If the returned ``RouteDecision``
         is ``confident``, accept it and accumulate cheap-tier cost.
      3. Otherwise, escalate to the frontier tier and accumulate frontier
         cost. The deterministic_hits counter is the headline KPI: every
         hit is one round-trip we did *not* pay for.
    """

    deterministic: DeterministicRouter
    cheap: Optional[TierCallable] = None
    frontier: Optional[TierCallable] = None
    cheap_cost: TierCost = field(default_factory=lambda: DEFAULT_CHEAP_TIER)
    frontier_cost: TierCost = field(default_factory=lambda: DEFAULT_FRONTIER_TIER)
    metrics: CostMetrics = field(default_factory=CostMetrics)

    def _bill(
        self, tier_cost: TierCost, input_tokens: int, output_tokens: int,
    ) -> float:
        return (
            tier_cost.input_usd_per_mtok * max(0, input_tokens)
            + tier_cost.output_usd_per_mtok * max(0, output_tokens)
        ) / 1_000_000

    def decide(self, text: str) -> RouteDecision:
        if not isinstance(text, str) or not text.strip():
            self.metrics.empty_or_invalid += 1
            return RouteDecision(intent="empty", confident=False)

        decision = self.deterministic.route(text)
        if decision.is_match:
            self.metrics.deterministic_hits += 1
            return decision

        if self.cheap is not None:
            tr = self.cheap(text)
            self.metrics.cheap_tokens_in += tr.input_tokens
            self.metrics.cheap_tokens_out += tr.output_tokens
            self.metrics.cheap_usd += self._bill(
                self.cheap_cost, tr.input_tokens, tr.output_tokens,
            )
            if tr.decision.confident:
                self.metrics.cheap_hits += 1
                return tr.decision

        if self.frontier is not None:
            tr = self.frontier(text)
            self.metrics.frontier_tokens_in += tr.input_tokens
            self.metrics.frontier_tokens_out += tr.output_tokens
            self.metrics.frontier_usd += self._bill(
                self.frontier_cost, tr.input_tokens, tr.output_tokens,
            )
            self.metrics.frontier_hits += 1
            return tr.decision

        # No cheap / frontier configured and deterministic missed.
        self.metrics.empty_or_invalid += 1
        return RouteDecision(intent="unrouted", confident=False)

    def projected_savings(
        self,
        baseline_tier: Optional[TierCost] = None,
    ) -> Dict[str, float]:
        """Estimate $$ saved vs an "always-baseline" policy.

        ``baseline_tier`` defaults to the frontier tier — i.e. assume the
        naïve setup would have called the expensive model on every request.
        Returns absolute spend + savings + savings-pct.
        """

        baseline = baseline_tier or self.frontier_cost
        baseline_total = baseline.avg_usd() * self.metrics.total_requests
        actual = self.metrics.total_usd
        saved = max(0.0, baseline_total - actual)
        return {
            "baseline_usd": round(baseline_total, 6),
            "actual_usd": round(actual, 6),
            "saved_usd": round(saved, 6),
            "saved_pct": round(
                100.0 * saved / baseline_total if baseline_total else 0.0, 2,
            ),
        }
