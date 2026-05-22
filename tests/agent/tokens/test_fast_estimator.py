"""Tests for ``agent.tokens.fast_estimator`` (Proposta I)."""

from __future__ import annotations

import pytest

from agent.tokens import (
    EstimatorBackend,
    estimate,
    estimate_throughput,
    has_tiktoken,
    naive_estimate,
)


def test_empty_string_yields_zero() -> None:
    assert estimate("") == 0
    assert naive_estimate("") == 0


def test_naive_estimate_uses_4_chars_per_token() -> None:
    assert naive_estimate("a" * 40) == 10
    assert naive_estimate("a" * 41) == 10
    assert naive_estimate("a" * 44) == 11


def test_estimate_returns_positive_int_for_real_text() -> None:
    n = estimate("The quick brown fox jumps over the lazy dog.")
    assert isinstance(n, int)
    assert n > 0


def test_throughput_smoke_naive_path() -> None:
    sample = estimate_throughput(
        ["hello world"] * 5, iters=50, model=None,
    )
    assert sample.samples == 50
    assert sample.median_us_per_call >= 0
    assert sample.texts_per_second > 0
    assert sample.backend in (
        EstimatorBackend.NAIVE, EstimatorBackend.TIKTOKEN,
    )


def test_has_tiktoken_returns_bool() -> None:
    assert isinstance(has_tiktoken(), bool)


def test_estimate_with_tiktoken_when_available() -> None:
    if not has_tiktoken():
        pytest.skip("tiktoken not installed")
    n_tt = estimate("The quick brown fox jumps over the lazy dog.",
                    model="gpt-4o")
    # tiktoken gives ~10 tokens for that sentence
    assert 6 <= n_tt <= 14
