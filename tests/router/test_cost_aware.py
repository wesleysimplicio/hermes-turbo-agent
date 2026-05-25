"""Tests for ``agent.router.cost_aware`` (Proposta B)."""

from __future__ import annotations

import pytest

from agent.router.cost_aware import (
    CostAwareRouter,
    DEFAULT_CHEAP_TIER,
    DEFAULT_FRONTIER_TIER,
    TierResult,
)
from agent.router.deterministic import DeterministicRouter, RouteDecision, RouteRule


@pytest.fixture()
def determ() -> DeterministicRouter:
    r = DeterministicRouter()
    r.add_rule(RouteRule.from_regex(
        "greet", r"^(hi|hello|oi|olá)$", lambda _t, _m: "hello back",
    ))
    return r


def test_deterministic_hit_costs_nothing(determ: DeterministicRouter) -> None:
    router = CostAwareRouter(
        deterministic=determ,
        cheap=lambda _t: TierResult(RouteDecision(intent="cheap", answer="x")),
        frontier=lambda _t: TierResult(RouteDecision(intent="frontier", answer="y")),
    )
    decision = router.decide("hi")
    assert decision.is_match
    assert router.metrics.deterministic_hits == 1
    assert router.metrics.cheap_hits == 0
    assert router.metrics.frontier_hits == 0
    assert router.metrics.total_usd == 0.0


def test_cheap_tier_accepted_when_confident(determ: DeterministicRouter) -> None:
    def cheap(_text: str) -> TierResult:
        return TierResult(
            decision=RouteDecision(intent="answer", answer="42", confident=True),
            input_tokens=200, output_tokens=100,
        )

    router = CostAwareRouter(deterministic=determ, cheap=cheap)
    decision = router.decide("how many?")
    assert decision.answer == "42"
    assert router.metrics.cheap_hits == 1
    assert router.metrics.frontier_hits == 0
    assert router.metrics.cheap_usd > 0


def test_low_confidence_cheap_escalates_to_frontier(
    determ: DeterministicRouter,
) -> None:
    def cheap(_text: str) -> TierResult:
        return TierResult(
            decision=RouteDecision(intent="weak", answer=None, confident=False),
            input_tokens=200, output_tokens=50,
        )

    def frontier(_text: str) -> TierResult:
        return TierResult(
            decision=RouteDecision(intent="strong", answer="final", confident=True),
            input_tokens=300, output_tokens=200,
        )

    router = CostAwareRouter(
        deterministic=determ, cheap=cheap, frontier=frontier,
    )
    decision = router.decide("write me a quicksort")
    assert decision.answer == "final"
    assert router.metrics.cheap_hits == 0  # cheap tried but not accepted
    assert router.metrics.frontier_hits == 1
    assert router.metrics.cheap_usd > 0  # cheap was still billed
    assert router.metrics.frontier_usd > router.metrics.cheap_usd


def test_empty_input_short_circuits(determ: DeterministicRouter) -> None:
    router = CostAwareRouter(
        deterministic=determ,
        cheap=lambda _t: TierResult(RouteDecision(intent="x", answer="y")),
    )
    router.decide("")
    router.decide("   ")
    assert router.metrics.empty_or_invalid == 2
    assert router.metrics.total_usd == 0.0


def test_projected_savings_when_all_deterministic(
    determ: DeterministicRouter,
) -> None:
    router = CostAwareRouter(deterministic=determ)
    for _ in range(10):
        router.decide("hi")
    proj = router.projected_savings()
    assert proj["actual_usd"] == 0.0
    assert proj["baseline_usd"] > 0
    assert proj["saved_pct"] == 100.0


def test_projected_savings_with_mixed_traffic(
    determ: DeterministicRouter,
) -> None:
    cheap_calls = [TierResult(
        decision=RouteDecision(intent="ok", answer="z", confident=True),
        input_tokens=200, output_tokens=80,
    )]

    def cheap(_text: str) -> TierResult:
        return cheap_calls[0]

    router = CostAwareRouter(
        deterministic=determ,
        cheap=cheap,
        cheap_cost=DEFAULT_CHEAP_TIER,
        frontier_cost=DEFAULT_FRONTIER_TIER,
    )
    # 8 deterministic + 2 cheap
    for _ in range(8):
        router.decide("hi")
    for _ in range(2):
        router.decide("write me something")

    assert router.metrics.deterministic_hits == 8
    assert router.metrics.cheap_hits == 2
    assert router.metrics.frontier_hits == 0
    proj = router.projected_savings()
    # baseline assumes frontier on every request, much more expensive
    assert proj["saved_usd"] > router.metrics.cheap_usd
    assert 80.0 < proj["saved_pct"] < 100.0
