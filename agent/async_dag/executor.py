"""Dependency-aware async tool batch executor.

Upstream Hermes already parallelises independent tools (``parallel_tool_batch``
showed ~5× over sequential). But it does not *infer* dependencies: callers
must declare batches manually. This module adds a DAG resolver that:

1. Accepts a list of ``DagNode`` (one per planned tool call).
2. Computes topological levels via Kahn's algorithm.
3. Runs each level in parallel via ``asyncio.gather``.
4. Feeds outputs of upstream nodes into placeholders inside downstream
   arguments (``$ref:<node_id>``).

Pure stdlib (``asyncio``, ``collections``). No external scheduler. Errors
short-circuit the level they happen on and surface as ``DagError``.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Mapping, Optional, Sequence


class DagError(RuntimeError):
    """Raised when the DAG cannot be built (cycle, missing dep, etc.)."""


ToolCallable = Callable[[str, Mapping[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class DagNode:
    """One planned tool invocation.

    ``args`` may contain references of the form ``"$ref:<other_node_id>"``
    (string-typed) or ``{"$ref": "<other_node_id>"}`` (dict-typed). The
    executor resolves them to the corresponding upstream output before
    invoking ``tool``.
    """

    node_id: str
    tool: str
    args: Mapping[str, Any] = field(default_factory=dict)
    depends_on: tuple[str, ...] = ()


@dataclass
class DagResult:
    outputs: Dict[str, Any]
    errors: Dict[str, BaseException]
    levels: List[List[str]]
    elapsed_s: float

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "node_count": len(self.outputs) + len(self.errors),
            "errors": {k: repr(v) for k, v in self.errors.items()},
            "levels": [list(level) for level in self.levels],
            "elapsed_s": round(self.elapsed_s, 4),
        }


def _topo_levels(nodes: Sequence[DagNode]) -> List[List[str]]:
    """Group nodes into topological levels using Kahn's algorithm."""

    by_id: Dict[str, DagNode] = {n.node_id: n for n in nodes}
    if len(by_id) != len(nodes):
        raise DagError("duplicate node_id")

    indeg: Dict[str, int] = {n.node_id: 0 for n in nodes}
    children: Dict[str, List[str]] = defaultdict(list)
    for n in nodes:
        for dep in n.depends_on:
            if dep not in by_id:
                raise DagError(f"node {n.node_id} depends on unknown {dep!r}")
            indeg[n.node_id] += 1
            children[dep].append(n.node_id)

    ready = deque(nid for nid, d in indeg.items() if d == 0)
    levels: List[List[str]] = []
    visited = 0
    while ready:
        level = list(ready)
        ready.clear()
        levels.append(level)
        for nid in level:
            visited += 1
            for child in children[nid]:
                indeg[child] -= 1
                if indeg[child] == 0:
                    ready.append(child)

    if visited != len(nodes):
        raise DagError("cycle detected in DAG")
    return levels


def _resolve_refs(value: Any, outputs: Mapping[str, Any]) -> Any:
    if isinstance(value, str) and value.startswith("$ref:"):
        ref = value[5:]
        if ref not in outputs:
            raise DagError(f"unresolved $ref:{ref}")
        return outputs[ref]
    if isinstance(value, dict):
        if "$ref" in value and len(value) == 1:
            ref = value["$ref"]
            if not isinstance(ref, str) or ref not in outputs:
                raise DagError(f"unresolved $ref dict {value!r}")
            return outputs[ref]
        return {k: _resolve_refs(v, outputs) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_refs(v, outputs) for v in value]
    return value


def build_dag(nodes: Sequence[DagNode]) -> List[List[str]]:
    """Public helper — returns topo levels without executing."""

    return _topo_levels(list(nodes))


@dataclass
class DagExecutor:
    dispatch: ToolCallable
    max_concurrency: int = 16

    async def run(self, nodes: Sequence[DagNode]) -> DagResult:
        loop = asyncio.get_event_loop()
        t0 = loop.time()
        by_id: Dict[str, DagNode] = {n.node_id: n for n in nodes}
        levels = _topo_levels(list(nodes))
        sem = asyncio.Semaphore(self.max_concurrency)
        outputs: Dict[str, Any] = {}
        errors: Dict[str, BaseException] = {}

        async def _run_one(node_id: str) -> None:
            async with sem:
                node = by_id[node_id]
                if any(dep in errors for dep in node.depends_on):
                    errors[node_id] = DagError(
                        f"upstream dep failed for {node_id}",
                    )
                    return
                try:
                    resolved = _resolve_refs(node.args, outputs)
                    result = await self.dispatch(node.tool, resolved)
                except BaseException as exc:  # noqa: BLE001
                    errors[node_id] = exc
                    return
                outputs[node_id] = result

        for level in levels:
            await asyncio.gather(*(_run_one(nid) for nid in level))

        return DagResult(
            outputs=outputs,
            errors=errors,
            levels=levels,
            elapsed_s=loop.time() - t0,
        )
