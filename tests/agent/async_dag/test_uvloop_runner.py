"""Tests for ``agent.async_dag.uvloop_runner`` (Proposta F)."""

from __future__ import annotations

import asyncio

import pytest

from agent.async_dag.uvloop_runner import (
    BatchMetrics,
    install_uvloop_if_available,
    run_batch,
    run_batch_async,
)


async def _noop(_i: int) -> int:
    return _i * 2


async def _fail(_i: int) -> int:
    raise RuntimeError("boom")


def test_install_uvloop_returns_string() -> None:
    policy = install_uvloop_if_available()
    assert policy in ("asyncio", "uvloop")


def test_run_batch_runs_and_orders_outputs() -> None:
    result = run_batch(_noop, 50, max_concurrency=8)
    assert result.metrics.scheduled == 50
    assert result.metrics.completed == 50
    assert result.metrics.errored == 0
    assert result.outputs == [i * 2 for i in range(50)]
    assert result.metrics.elapsed_s > 0
    assert result.metrics.throughput_per_s > 0


def test_run_batch_collects_errors() -> None:
    async def factory(i: int) -> int:
        if i % 2 == 0:
            return i
        raise RuntimeError(f"fail-{i}")

    result = run_batch(factory, 10, max_concurrency=4)
    assert result.metrics.completed == 5
    assert result.metrics.errored == 5
    assert all(isinstance(e, RuntimeError) for e in result.errors)


def test_metrics_throughput_zero_on_zero_elapsed() -> None:
    m = BatchMetrics(scheduled=10, completed=10, elapsed_s=0)
    assert m.throughput_per_s == 0.0


def test_run_batch_async_works() -> None:
    async def runner() -> int:
        result = await run_batch_async(_noop, 20)
        return result.metrics.completed

    assert asyncio.run(runner()) == 20
