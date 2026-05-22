"""Fast token-count estimator (Proposta I — tiktoken / Rust-backed)."""

from agent.tokens.fast_estimator import (
    EstimatorBackend,
    estimate,
    estimate_throughput,
    has_tiktoken,
    naive_estimate,
)

__all__ = [
    "EstimatorBackend",
    "estimate",
    "estimate_throughput",
    "has_tiktoken",
    "naive_estimate",
]
