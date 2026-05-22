"""Tests for ``agent.providers.fallback_chain`` (Proposta E)."""

from __future__ import annotations

import asyncio

import pytest

from agent.providers import ProviderChain, is_transient
from agent.providers.fallback_chain import AsyncProviderChain


def _ok(name: str):
    def _call(prompt: str) -> str:
        return f"{name}:{prompt}"

    return _call


def _fail_transient(_prompt: str) -> str:
    raise RuntimeError("429 Too Many Requests")


def _fail_fatal(_prompt: str) -> str:
    raise ValueError("invalid api key")


def test_is_transient_classifier() -> None:
    assert is_transient(RuntimeError("rate limit hit"))
    assert is_transient(TimeoutError("timeout"))
    assert is_transient(ConnectionError("connection reset by peer"))
    assert not is_transient(ValueError("bad request"))


def test_first_provider_succeeds() -> None:
    chain = ProviderChain(providers=[("p1", _ok("p1"))], sleep=lambda _: None)
    result = chain.call("hello")
    assert result.provider == "p1"
    assert result.response == "p1:hello"
    assert chain.metrics.attempts == 1
    assert chain.metrics.switches == 0


def test_falls_through_to_second_after_transient_retries() -> None:
    state = {"n": 0}

    def flaky(_p: str) -> str:
        state["n"] += 1
        raise RuntimeError("429 rate limit")

    chain = ProviderChain(
        providers=[("p1", flaky), ("p2", _ok("p2"))],
        max_retries=2,
        base_delay_s=0.0,
        sleep=lambda _: None,
    )
    result = chain.call("hi")
    assert result.provider == "p2"
    assert chain.metrics.switches == 1
    assert state["n"] == 3  # initial + 2 retries before giving up on p1


def test_fatal_error_skips_immediately_to_next() -> None:
    chain = ProviderChain(
        providers=[("p1", _fail_fatal), ("p2", _ok("p2"))],
        max_retries=5,
        sleep=lambda _: None,
    )
    result = chain.call("x")
    assert result.provider == "p2"
    # only one failure on p1 because the error was classified fatal
    assert chain.metrics.failures_per_provider == {"p1": 1}


def test_all_providers_exhaust_raises() -> None:
    chain = ProviderChain(
        providers=[("p1", _fail_transient), ("p2", _fail_transient)],
        max_retries=1,
        sleep=lambda _: None,
    )
    with pytest.raises(RuntimeError):
        chain.call("x")


def test_async_chain_works() -> None:
    async def ok_async(prompt: str) -> str:
        return f"async:{prompt}"

    chain = AsyncProviderChain(providers=[("a", ok_async)])

    async def runner():
        return await chain.call("hi")

    result = asyncio.run(runner())
    assert result.provider == "a"
    assert result.response == "async:hi"
