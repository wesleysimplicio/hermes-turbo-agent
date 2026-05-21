"""LLM fallback wrapper for the deterministic router. Stdlib-only."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .deterministic import DeterministicRouter, RouteDecision

LLMCallable = Callable[[str], RouteDecision]


@dataclass
class RouterMetrics:
    deterministic_hits: int = 0
    llm_escalations: int = 0
    empty_or_invalid: int = 0

    @property
    def total(self) -> int:
        return self.deterministic_hits + self.llm_escalations + self.empty_or_invalid

    @property
    def avoided_llm_calls(self) -> int:
        return self.deterministic_hits

    def as_dict(self) -> dict:
        return {
            "deterministic_hits": self.deterministic_hits,
            "llm_escalations": self.llm_escalations,
            "empty_or_invalid": self.empty_or_invalid,
            "total": self.total,
            "avoided_llm_calls": self.avoided_llm_calls,
        }


@dataclass
class RouterWithFallback:
    router: DeterministicRouter
    llm: Optional[LLMCallable] = None
    metrics: RouterMetrics = field(default_factory=RouterMetrics)

    def decide(self, text: str) -> RouteDecision:
        decision = self.router.route(text)
        if decision.is_match:
            self.metrics.deterministic_hits += 1
            return decision
        if decision.intent == "empty" or not isinstance(text, str) or self.llm is None:
            self.metrics.empty_or_invalid += 1
            return decision
        self.metrics.llm_escalations += 1
        result = self.llm(text)
        if not isinstance(result, RouteDecision):
            return RouteDecision(intent="llm", answer=str(result), confident=False)
        return result
