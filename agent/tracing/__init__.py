"""Lightweight OTel-compatible tracing (Proposta D)."""

from agent.tracing.spans import (
    Span,
    SpanRecorder,
    SpanStatus,
    current_recorder,
    set_default_recorder,
    span,
)

__all__ = [
    "Span",
    "SpanRecorder",
    "SpanStatus",
    "current_recorder",
    "set_default_recorder",
    "span",
]
