"""Compact skill manifests with lazy body loading.

Default skill representation is ``SkillManifest(name, trigger,
steps_summary)``. The full SKILL.md body is loaded on demand via
:func:`load_skill_body`. See ``docs/perf/lazy-schemas.md``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Dict, List

BodyLoader = Callable[[], str]


@dataclass(frozen=True)
class SkillManifest:
    """Minimal skill descriptor kept in memory."""

    name: str
    trigger: str
    steps_summary: str


class SkillRegistry:
    """Registry of skill manifests + body loaders (body cached on first load)."""

    def __init__(self) -> None:
        self._manifests: Dict[str, SkillManifest] = {}
        self._loaders: Dict[str, BodyLoader] = {}
        self._bodies: Dict[str, str] = {}
        self._lock = Lock()

    def register(
        self, name: str, trigger: str, steps_summary: str, body_loader: BodyLoader
    ) -> SkillManifest:
        if not name:
            raise ValueError("skill name must be non-empty")
        if not callable(body_loader):
            raise TypeError("body_loader must be callable")
        manifest = SkillManifest(name=name, trigger=trigger, steps_summary=steps_summary)
        with self._lock:
            self._manifests[name] = manifest
            self._loaders[name] = body_loader
            self._bodies.pop(name, None)
        return manifest

    def register_path(
        self, name: str, trigger: str, steps_summary: str, body_path
    ) -> SkillManifest:
        path = Path(body_path)
        return self.register(
            name, trigger, steps_summary, lambda: path.read_text(encoding="utf-8")
        )

    def list(self) -> List[SkillManifest]:
        with self._lock:
            return list(self._manifests.values())

    def load_body(self, name: str) -> str:
        with self._lock:
            cached = self._bodies.get(name)
            if cached is not None:
                return cached
            loader = self._loaders.get(name)
            if loader is None:
                raise KeyError(f"skill not registered: {name}")
        body = loader()
        if not isinstance(body, str):
            raise TypeError(
                f"body loader for {name!r} must return str, got {type(body).__name__}"
            )
        with self._lock:
            self._bodies[name] = body
        return body

    def stats(self) -> Dict[str, int]:
        with self._lock:
            return {"registered": len(self._manifests), "loaded": len(self._bodies)}

    def clear(self) -> None:
        with self._lock:
            self._manifests.clear()
            self._loaders.clear()
            self._bodies.clear()


_default = SkillRegistry()

register_skill = _default.register
list_skills = _default.list
load_skill_body = _default.load_body
_reset_default_registry_for_tests = _default.clear
