"""Tests for ``agent.governor`` budget + policies."""

from __future__ import annotations

import pytest

from agent.governor import (
    BudgetConfig,
    BudgetExceeded,
    BudgetGovernor,
    EscalationLevel,
    WarnAt70HardStopAt100,
)


def test_budget_under_limit_records_without_raising():
    gov = BudgetGovernor(BudgetConfig(max_tokens_per_loop=1000))
    snap = gov.record_step(tokens=100)
    assert snap.tokens == 100
    assert snap.iterations == 1


def test_budget_raises_when_tokens_exceed_limit():
    gov = BudgetGovernor(BudgetConfig(max_tokens_per_loop=200))
    gov.record_step(tokens=150)
    with pytest.raises(BudgetExceeded) as info:
        gov.record_step(tokens=80)
    assert info.value.axis == "tokens"
    assert info.value.used == 230
    assert info.value.limit == 200


def test_budget_raises_when_cost_exceed_limit():
    gov = BudgetGovernor(BudgetConfig(max_cost_usd=1.0))
    with pytest.raises(BudgetExceeded) as info:
        gov.record_step(cost_usd=1.25)
    assert info.value.axis == "cost_usd"


def test_budget_raises_when_iterations_exceed_limit():
    gov = BudgetGovernor(BudgetConfig(max_iterations=2))
    gov.record_step(tokens=1)
    with pytest.raises(BudgetExceeded) as info:
        gov.record_step(tokens=1)
    assert info.value.axis == "iterations"


def test_budget_rejects_negative_inputs():
    gov = BudgetGovernor(BudgetConfig(max_tokens_per_loop=100))
    with pytest.raises(ValueError):
        gov.record_step(tokens=-5)
    with pytest.raises(ValueError):
        gov.record_step(cost_usd=-0.1)


def test_warn_callback_fires_once_per_axis_at_threshold():
    fired = []

    def on_warn(axis, snap):
        fired.append(axis)

    gov = BudgetGovernor(
        BudgetConfig(max_tokens_per_loop=100),
        warn_ratio=0.70,
        on_warn=on_warn,
    )
    gov.record_step(tokens=50)
    assert fired == []
    gov.record_step(tokens=25)  # 75 / 100 = 75%
    assert fired == ["tokens"]
    with pytest.raises(BudgetExceeded):
        gov.record_step(tokens=30)
    assert fired == ["tokens"]


def test_no_limits_means_no_enforcement():
    gov = BudgetGovernor(BudgetConfig())
    for _ in range(1000):
        gov.record_step(tokens=10_000, cost_usd=1.0)
    assert gov.snapshot().iterations == 1000


def test_policy_returns_ok_warn_stop_in_order():
    cfg = BudgetConfig(max_tokens_per_loop=100)
    policy = WarnAt70HardStopAt100()
    gov = BudgetGovernor(cfg)

    gov.record_step(tokens=10)
    assert policy.evaluate(gov.snapshot(), cfg) == EscalationLevel.OK

    gov.record_step(tokens=65)  # 75%
    assert policy.evaluate(gov.snapshot(), cfg) == EscalationLevel.WARN

    try:
        gov.record_step(tokens=30)
    except BudgetExceeded:
        pass
    assert policy.evaluate(gov.snapshot(), cfg) == EscalationLevel.STOP


def test_policy_max_ratio_picks_highest_axis():
    cfg = BudgetConfig(max_tokens_per_loop=1000, max_cost_usd=10.0)
    gov = BudgetGovernor(cfg)
    gov.record_step(tokens=100, cost_usd=8.0)  # 10% tokens, 80% cost
    assert WarnAt70HardStopAt100().evaluate(gov.snapshot(), cfg) == EscalationLevel.WARN
