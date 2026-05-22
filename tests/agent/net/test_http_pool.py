"""Tests for ``agent.net.http_pool`` (Proposta J)."""

from __future__ import annotations

import asyncio

import pytest

from agent.net import HttpPool, HttpPoolUnavailable
from agent.net.http_pool import _HAS_HTTPX


def test_pool_construction_is_cheap() -> None:
    pool = HttpPool(base_url="https://example.com")
    assert pool.base_url == "https://example.com"
    assert pool._client is None
    assert pool.metrics.requests == 0


def test_using_pool_without_aenter_raises() -> None:
    pool = HttpPool()
    with pytest.raises(RuntimeError):
        asyncio.run(pool.get("/"))


def test_pool_raises_when_httpx_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("agent.net.http_pool._HAS_HTTPX", False)
    pool = HttpPool()
    with pytest.raises(HttpPoolUnavailable):
        asyncio.run(pool.__aenter__())


@pytest.mark.skipif(not _HAS_HTTPX, reason="httpx not installed")
def test_pool_collects_metrics() -> None:
    import httpx

    transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"ok": True})
    )

    async def runner() -> dict:
        pool = HttpPool(base_url="https://example.com", http2=False)
        async with pool:
            # swap in the mock transport
            assert pool._client is not None
            pool._client._transport = transport
            r = await pool.get("/health")
            assert r.status_code == 200
        return pool.metrics.as_dict()

    metrics = asyncio.run(runner())
    assert metrics["requests"] == 1
    assert metrics["errors"] == 0
