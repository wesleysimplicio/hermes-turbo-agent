"""Deterministic tool-call replay on top of content-addressable receipts.

Improves upstream Hermes by adding a *replay primitive* for tool calls:
when an agent re-invokes a tool with the same arguments, return the cached
output instead of re-executing. This is what upstream Hermes lacks — skills
are auto-generated post-task, but tool outputs themselves are not replayable.

Key ideas:
- Canonical key = ``sha256(name || canonical_json(args))``.
- Storage = ``<dir>/tool/<sha>.json`` (separate sub-tree from action receipts
  so they can be rotated independently).
- ``record_tool_call`` is append-only; second call with same key is a no-op.
- ``replay_if_hit`` returns the cached output or ``None``.
- ``ToolReplayMetrics`` tracks hits/misses so we can quantify cache value.

This module is stdlib-only and additive — it does not modify
``record_receipt`` or change the on-disk schema of action receipts.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

_DIR_ENV = "HERMES_RECEIPTS_DIR"


def default_replay_dir(root: Optional[str | Path] = None) -> Path:
    """Resolve the replay-store directory.

    Order:
    1. ``$HERMES_RECEIPTS_DIR/tool`` if the env is set.
    2. ``<root or cwd>/.receipts/tool``.
    """

    override = os.environ.get(_DIR_ENV)
    if override:
        return Path(override).expanduser() / "tool"
    base = Path(root).expanduser() if root else Path.cwd()
    return base / ".receipts" / "tool"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_args(args: Mapping[str, Any] | None) -> str:
    """JSON-encode ``args`` with sorted keys + tight separators.

    None and missing args both map to ``"{}"`` so a tool called with no
    arguments has a stable key.
    """

    if args is None:
        return "{}"
    return json.dumps(args, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def tool_call_key(name: str, args: Mapping[str, Any] | None) -> str:
    """Deterministic BLAKE2b key for ``(name, args)`` pair.

    Same name + same args (any key order) → same key. Different by one
    character → different key. Safe to commit alongside skill snapshots.

    BLAKE2b at 32-byte digest is sha256-strength but stdlib-faster.
    For empty/no-args case we short-circuit the JSON canonicalisation
    so the hot path stays sub-microsecond on simple tool calls.
    """

    if args is None or len(args) == 0:
        blob = f"{name}::{{}}".encode("utf-8")
    else:
        blob = f"{name}::{_canonical_args(args)}".encode("utf-8")
    return hashlib.blake2b(blob, digest_size=32).hexdigest()


@dataclass(frozen=True)
class ToolCallRecord:
    sha: str
    name: str
    args_canonical: str
    output: Any
    status: str = "ok"
    elapsed_ms: int = 0
    ts: str = field(default_factory=_utc_now)
    meta: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["meta"] = dict(self.meta)
        return data


def replay_path(sha: str, directory: Optional[Path] = None) -> Path:
    base = directory or default_replay_dir()
    return base / f"{sha}.json"


def record_tool_call(
    *,
    name: str,
    args: Mapping[str, Any] | None,
    output: Any,
    status: str = "ok",
    elapsed_ms: int = 0,
    meta: Optional[Mapping[str, Any]] = None,
    directory: Optional[Path] = None,
) -> ToolCallRecord:
    """Persist a tool call output for later replay.

    Append-only: if the same (name, args) already has a record, return the
    existing record unchanged.
    """

    sha = tool_call_key(name, args)
    base = directory or default_replay_dir()
    target = base / f"{sha}.json"

    if target.exists():
        try:
            data = json.loads(target.read_text(encoding="utf-8"))
            return ToolCallRecord(
                sha=data.get("sha", sha),
                name=data.get("name", name),
                args_canonical=data.get("args_canonical", _canonical_args(args)),
                output=data.get("output"),
                status=data.get("status", status),
                elapsed_ms=int(data.get("elapsed_ms", 0)),
                ts=data.get("ts", _utc_now()),
                meta=data.get("meta", {}) or {},
            )
        except (OSError, json.JSONDecodeError):
            pass

    record = ToolCallRecord(
        sha=sha,
        name=name,
        args_canonical=_canonical_args(args),
        output=output,
        status=status,
        elapsed_ms=elapsed_ms,
        meta=dict(meta or {}),
    )

    try:
        base.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(record.to_dict(), separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass

    return record


def replay_if_hit(
    name: str,
    args: Mapping[str, Any] | None,
    directory: Optional[Path] = None,
) -> Optional[ToolCallRecord]:
    """Return a previously-recorded tool-call output for ``(name, args)``.

    Returns ``None`` on miss, corrupt file, or unreadable storage. Never
    raises — the caller falls back to re-executing the tool.
    """

    sha = tool_call_key(name, args)
    target = (directory or default_replay_dir()) / f"{sha}.json"
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return ToolCallRecord(
        sha=data.get("sha", sha),
        name=data.get("name", name),
        args_canonical=data.get("args_canonical", _canonical_args(args)),
        output=data.get("output"),
        status=data.get("status", "ok"),
        elapsed_ms=int(data.get("elapsed_ms", 0)),
        ts=data.get("ts", _utc_now()),
        meta=data.get("meta", {}) or {},
    )


@dataclass
class ToolReplayMetrics:
    hits: int = 0
    misses: int = 0
    elapsed_ms_saved: int = 0

    @property
    def total(self) -> int:
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        return self.hits / self.total if self.total else 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": self.total,
            "hit_rate": round(self.hit_rate, 4),
            "elapsed_ms_saved": self.elapsed_ms_saved,
        }


@dataclass
class ToolReplayer:
    """Stateful helper bundling lookup + record + metrics.

    Use this when wrapping a tool dispatcher. The two-step pattern is::

        replayer = ToolReplayer(directory=path)
        cached = replayer.lookup(name, args)
        if cached is not None:
            return cached.output
        out = original_dispatch(name, args)
        replayer.observe(name, args, out, elapsed_ms=measured)
        return out
    """

    directory: Optional[Path] = None
    metrics: ToolReplayMetrics = field(default_factory=ToolReplayMetrics)

    def lookup(
        self, name: str, args: Mapping[str, Any] | None
    ) -> Optional[ToolCallRecord]:
        rec = replay_if_hit(name, args, self.directory)
        if rec is None:
            self.metrics.misses += 1
            return None
        self.metrics.hits += 1
        self.metrics.elapsed_ms_saved += rec.elapsed_ms
        return rec

    def observe(
        self,
        name: str,
        args: Mapping[str, Any] | None,
        output: Any,
        *,
        elapsed_ms: int = 0,
        status: str = "ok",
        meta: Optional[Mapping[str, Any]] = None,
    ) -> ToolCallRecord:
        return record_tool_call(
            name=name, args=args, output=output, status=status,
            elapsed_ms=elapsed_ms, meta=meta, directory=self.directory,
        )
