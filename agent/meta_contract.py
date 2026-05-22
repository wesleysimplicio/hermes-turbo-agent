"""Load and evaluate the ``.hermes-meta.json`` containment contract (P2).

Inspired by ``.starter-meta.json`` from ``wesleysimplicio/llm-project-mapper``.
Adds executable enforcement to the otherwise text-only rules in CLAUDE.md.

Usage::

    from agent.meta_contract import load_meta, check_write

    meta = load_meta(".")
    decision = check_write(meta, "agent/foo.py")
    if decision.blocked:
        raise PermissionError(decision.reason)
"""

from __future__ import annotations

import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence


META_FILENAME = ".hermes-meta.json"


@dataclass(frozen=True)
class HermesMeta:
    """Parsed view of ``.hermes-meta.json``."""

    root: str
    managed_paths: tuple[str, ...] = ()
    read_only_globs: tuple[str, ...] = ()
    init_must_merge: tuple[str, ...] = ()
    init_must_ask: tuple[str, ...] = ()
    on_read_only_violation: str = "block"
    on_init_must_merge: str = "warn"
    on_init_must_ask: str = "ask"


@dataclass(frozen=True)
class WriteDecision:
    """Decision returned by ``check_write``."""

    blocked: bool
    action: str  # "allow" | "block" | "warn" | "ask"
    reason: str = ""
    rule: str = ""


def _as_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(v) for v in value if isinstance(v, (str, bytes)))


def load_meta(root: str | Path) -> Optional[HermesMeta]:
    """Load ``.hermes-meta.json`` from ``root``. Returns ``None`` if absent."""

    root_path = Path(root).expanduser().resolve()
    meta_file = root_path / META_FILENAME
    if not meta_file.is_file():
        return None
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    policy = data.get("policy") if isinstance(data.get("policy"), dict) else {}
    return HermesMeta(
        root=str(root_path),
        managed_paths=_as_tuple(data.get("managed_paths")),
        read_only_globs=_as_tuple(data.get("read_only_globs")),
        init_must_merge=_as_tuple(data.get("init_must_merge")),
        init_must_ask=_as_tuple(data.get("init_must_ask")),
        on_read_only_violation=str(policy.get("on_read_only_violation", "block")),
        on_init_must_merge=str(policy.get("on_init_must_merge", "warn")),
        on_init_must_ask=str(policy.get("on_init_must_ask", "ask")),
    )


def _relative(meta: HermesMeta, path: str | Path) -> Optional[str]:
    try:
        rel = Path(path).expanduser().resolve().relative_to(Path(meta.root))
    except (OSError, ValueError):
        return None
    return rel.as_posix()


def _match_any(rel_path: str, patterns: Sequence[str]) -> Optional[str]:
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat):
            return pat
    return None


def check_write(meta: HermesMeta, path: str | Path) -> WriteDecision:
    """Evaluate whether ``path`` may be written under ``meta``.

    Resolution order:
      1. read_only_globs → block (or configured action)
      2. init_must_ask  → ask
      3. init_must_merge → warn (merge, not overwrite)
      4. managed_paths   → allow
      5. otherwise       → warn (out-of-scope)
    """

    rel = _relative(meta, path)
    if rel is None:
        return WriteDecision(
            blocked=False, action="allow", reason="path outside meta root", rule=""
        )

    ro_hit = _match_any(rel, meta.read_only_globs)
    if ro_hit:
        blocked = meta.on_read_only_violation == "block"
        return WriteDecision(
            blocked=blocked,
            action=meta.on_read_only_violation,
            reason=f"{rel} matches read_only_glob {ro_hit!r}",
            rule="read_only_globs",
        )

    ask_hit = _match_any(rel, meta.init_must_ask)
    if ask_hit:
        return WriteDecision(
            blocked=meta.on_init_must_ask == "block",
            action=meta.on_init_must_ask,
            reason=f"{rel} matches init_must_ask {ask_hit!r}",
            rule="init_must_ask",
        )

    merge_hit = _match_any(rel, meta.init_must_merge)
    if merge_hit:
        return WriteDecision(
            blocked=False,
            action=meta.on_init_must_merge,
            reason=f"{rel} matches init_must_merge {merge_hit!r} — merge, do not overwrite",
            rule="init_must_merge",
        )

    managed_hit = _match_any(rel, meta.managed_paths)
    if managed_hit:
        return WriteDecision(
            blocked=False, action="allow",
            reason=f"{rel} matches managed_paths {managed_hit!r}",
            rule="managed_paths",
        )

    return WriteDecision(
        blocked=False, action="warn",
        reason=f"{rel} is out of scope of managed_paths",
        rule="out_of_scope",
    )


def list_violations(
    meta: HermesMeta, paths: Sequence[str | Path]
) -> List[WriteDecision]:
    """Batch helper. Returns only decisions where ``blocked`` is True."""

    return [d for d in (check_write(meta, p) for p in paths) if d.blocked]
