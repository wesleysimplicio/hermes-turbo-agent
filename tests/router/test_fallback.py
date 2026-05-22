"""Tests for the LLM fallback wrapper and metrics."""

from __future__ import annotations

from agent.router.deterministic import RouteDecision, default_router
from agent.router.fallback import RouterMetrics, RouterWithFallback


def _llm_stub(text: str) -> RouteDecision:
    return RouteDecision(intent="llm", answer=f"LLM:{text}", confident=False)


def test_deterministic_hit_does_not_call_llm() -> None:
    calls = []

    def llm(text: str) -> RouteDecision:
        calls.append(text)
        return _llm_stub(text)

    rwf = RouterWithFallback(router=default_router(), llm=llm)
    decision = rwf.decide("ping")
    assert decision.answer == "pong"
    assert calls == []
    assert rwf.metrics.deterministic_hits == 1
    assert rwf.metrics.llm_escalations == 0
    assert rwf.metrics.avoided_llm_calls == 1


def test_unknown_escalates_to_llm() -> None:
    rwf = RouterWithFallback(router=default_router(), llm=_llm_stub)
    decision = rwf.decide("please explain monoidal categories")
    assert decision.intent == "llm"
    assert decision.answer == "LLM:please explain monoidal categories"
    assert rwf.metrics.llm_escalations == 1
    assert rwf.metrics.deterministic_hits == 0


def test_no_llm_configured_returns_unknown() -> None:
    rwf = RouterWithFallback(router=default_router(), llm=None)
    decision = rwf.decide("rambling unknown text")
    assert decision.is_match is False
    assert decision.intent == "unknown"
    assert rwf.metrics.empty_or_invalid == 1
    assert rwf.metrics.llm_escalations == 0


def test_empty_does_not_escalate() -> None:
    rwf = RouterWithFallback(router=default_router(), llm=_llm_stub)
    decision = rwf.decide("   ")
    assert decision.intent == "empty"
    assert rwf.metrics.llm_escalations == 0
    assert rwf.metrics.empty_or_invalid == 1


def test_metrics_as_dict_shape() -> None:
    m = RouterMetrics(deterministic_hits=3, llm_escalations=1, empty_or_invalid=2)
    d = m.as_dict()
    assert d["total"] == 6
    assert d["avoided_llm_calls"] == 3
    assert set(d.keys()) >= {
        "deterministic_hits",
        "llm_escalations",
        "empty_or_invalid",
        "total",
        "avoided_llm_calls",
    }


def test_llm_returning_non_decision_is_wrapped() -> None:
    rwf = RouterWithFallback(
        router=default_router(),
        llm=lambda t: "plain string answer",  # type: ignore[return-value, arg-type]
    )
    decision = rwf.decide("opaque utterance")
    assert decision.intent == "llm"
    assert decision.answer == "plain string answer"
    assert decision.confident is False
