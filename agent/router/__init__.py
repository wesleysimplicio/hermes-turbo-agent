"""Deterministic routing for trivial runtime decisions.

Avoids LLM calls for decisions where regex / dictionary rules are sufficient.
See ``docs/runtime/deterministic-router.md`` for design and rationale.
"""
from .deterministic import (
    DeterministicRouter,
    RouteDecision,
    RouteRule,
    default_router,
)
from .fallback import RouterMetrics, RouterWithFallback

__all__ = [
    "DeterministicRouter",
    "RouteDecision",
    "RouteRule",
    "default_router",
    "RouterMetrics",
    "RouterWithFallback",
]
