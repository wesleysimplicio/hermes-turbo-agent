"""Tests for ``agent.async_dag.executor`` (Proposta C)."""

from __future__ import annotations

import asyncio

import pytest

from agent.async_dag import DagExecutor, DagNode, build_dag
from agent.async_dag.executor import DagError


async def _dispatch(tool: str, args):
    if tool == "fail":
        raise RuntimeError("boom")
    return {"tool": tool, "args": dict(args)}


def test_build_dag_simple_chain() -> None:
    nodes = [
        DagNode("a", "echo"),
        DagNode("b", "echo", args={"x": "$ref:a"}, depends_on=("a",)),
        DagNode("c", "echo", args={"y": "$ref:b"}, depends_on=("b",)),
    ]
    levels = build_dag(nodes)
    assert levels == [["a"], ["b"], ["c"]]


def test_build_dag_fans_out_and_in() -> None:
    nodes = [
        DagNode("a", "echo"),
        DagNode("b", "echo", depends_on=("a",)),
        DagNode("c", "echo", depends_on=("a",)),
        DagNode("d", "echo", depends_on=("b", "c")),
    ]
    levels = build_dag(nodes)
    assert levels[0] == ["a"]
    assert set(levels[1]) == {"b", "c"}
    assert levels[2] == ["d"]


def test_cycle_raises() -> None:
    nodes = [
        DagNode("a", "echo", depends_on=("b",)),
        DagNode("b", "echo", depends_on=("a",)),
    ]
    with pytest.raises(DagError):
        build_dag(nodes)


def test_unknown_dep_raises() -> None:
    nodes = [DagNode("a", "echo", depends_on=("zzz",))]
    with pytest.raises(DagError):
        build_dag(nodes)


def test_executor_runs_topologically() -> None:
    nodes = [
        DagNode("a", "alpha"),
        DagNode("b", "beta", args={"x": "$ref:a"}, depends_on=("a",)),
    ]
    ex = DagExecutor(dispatch=_dispatch)
    result = asyncio.run(ex.run(nodes))
    assert result.ok
    assert result.outputs["a"]["tool"] == "alpha"
    assert result.outputs["b"]["args"]["x"] == result.outputs["a"]


def test_executor_runs_level_in_parallel() -> None:
    timings: list[tuple[str, float]] = []

    async def slow(tool: str, args):
        await asyncio.sleep(0.05)
        timings.append((tool, asyncio.get_event_loop().time()))
        return tool

    ex = DagExecutor(dispatch=slow)
    nodes = [DagNode(f"n{i}", f"t{i}") for i in range(4)]
    result = asyncio.run(ex.run(nodes))
    assert result.ok
    # 4 parallel nodes each 50 ms should finish in well under 200 ms
    assert result.elapsed_s < 0.18


def test_failed_node_short_circuits_dependents() -> None:
    nodes = [
        DagNode("a", "fail"),
        DagNode("b", "echo", depends_on=("a",)),
    ]
    ex = DagExecutor(dispatch=_dispatch)
    result = asyncio.run(ex.run(nodes))
    assert not result.ok
    assert "a" in result.errors
    assert "b" in result.errors
    assert "upstream dep failed" in repr(result.errors["b"])
