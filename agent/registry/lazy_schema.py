"""On-demand tool JSON schema registry.

At startup, only ``(name, description)`` pairs are registered. The full
JSON schema is fetched the first time ``load_schema(name)`` is invoked
and cached. See ``docs/perf/lazy-schemas.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Callable, Dict, List, Mapping

SchemaLoader = Callable[[], Mapping[str, object]]


@dataclass(frozen=True)
class ToolStub:
    """Minimal tool entry kept in memory at startup."""

    name: str
    description: str


class LazyToolRegistry:
    """Registry of tool name -> stub + schema loader (cached on first load)."""

    def __init__(self) -> None:
        self._stubs: Dict[str, ToolStub] = {}
        self._loaders: Dict[str, SchemaLoader] = {}
        self._schemas: Dict[str, Mapping[str, object]] = {}
        self._lock = Lock()

    def register(
        self, name: str, description: str, schema_loader: SchemaLoader
    ) -> ToolStub:
        if not name:
            raise ValueError("tool name must be non-empty")
        if not callable(schema_loader):
            raise TypeError("schema_loader must be callable")
        stub = ToolStub(name=name, description=description)
        with self._lock:
            self._stubs[name] = stub
            self._loaders[name] = schema_loader
            self._schemas.pop(name, None)
        return stub

    def list(self) -> List[ToolStub]:
        with self._lock:
            return list(self._stubs.values())

    def load(self, name: str) -> Mapping[str, object]:
        with self._lock:
            cached = self._schemas.get(name)
            if cached is not None:
                return cached
            loader = self._loaders.get(name)
            if loader is None:
                raise KeyError(f"tool not registered: {name}")
        schema = loader()
        if not isinstance(schema, Mapping):
            raise TypeError(
                f"schema loader for {name!r} must return Mapping, got {type(schema).__name__}"
            )
        with self._lock:
            self._schemas[name] = schema
        return schema

    def stats(self) -> Mapping[str, int]:
        with self._lock:
            return {"registered": len(self._stubs), "loaded": len(self._schemas)}

    def clear(self) -> None:
        with self._lock:
            self._stubs.clear()
            self._loaders.clear()
            self._schemas.clear()


_default = LazyToolRegistry()

register_tool = _default.register
list_tools = _default.list
load_schema = _default.load
_reset_default_registry_for_tests = _default.clear
