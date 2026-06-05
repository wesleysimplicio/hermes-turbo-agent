"""Stage timing primitive: context manager that appends a JSONL event per stage.

Privacy: only stage name, duration, and coarse labels (provider/model/tool) are
captured. Never logs prompt content, secrets, or arbitrary user data. Callers
must pass already-redacted labels.

Usage:
    from agent.telemetry import StageTimer

    with StageTimer("context_build", provider="deepseek", model="deepseek-chat"):
        build_context(...)

The log path defaults to ``$HERMES_TELEMETRY_LOG`` or ``~/.hermes/telemetry.jsonl``.
File writes are best-effort; failures never raise into the hot path.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


_DEFAULT_LOG = Path.home() / ".hermes" / "telemetry.jsonl"
_log_path: Optional[Path] = None


def set_log_path(path: str | os.PathLike[str]) -> None:
    """Override the JSONL output path (mainly for tests)."""
    global _log_path
    _log_path = Path(path)


def get_log_path() -> Path:
    """Resolve the active JSONL output path."""
    if _log_path is not None:
        return _log_path
    env = os.environ.get("HERMES_TELEMETRY_LOG")
    return Path(env) if env else _DEFAULT_LOG


def record_stage(
    stage: str,
    duration_ms: float,
    *,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    tool: Optional[str] = None,
    ok: bool = True,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    """Append a single stage event to the JSONL log. Best-effort, never raises."""
    event = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "stage": stage,
        "duration_ms": round(float(duration_ms), 3),
        "provider": provider,
        "model": model,
        "tool": tool,
        "ok": bool(ok),
        "meta": meta or {},
    }
    try:
        path = get_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 - telemetry must never break runtime
        return


class StageTimer:
    """Context manager that times a runtime stage and emits a JSONL event.

    Sets ``ok=False`` automatically if the block raises. The exception still
    propagates; telemetry is side-effect only.
    """

    __slots__ = ("stage", "provider", "model", "tool", "meta", "_t0", "ok", "duration_ms")

    def __init__(
        self,
        stage: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        tool: Optional[str] = None,
        meta: Optional[dict[str, Any]] = None,
    ) -> None:
        self.stage = stage
        self.provider = provider
        self.model = model
        self.tool = tool
        self.meta = meta
        self._t0 = 0.0
        self.ok = True
        self.duration_ms = 0.0

    def __enter__(self) -> "StageTimer":
        self._t0 = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.duration_ms = (time.perf_counter() - self._t0) * 1000.0
        self.ok = exc_type is None
        record_stage(
            self.stage,
            self.duration_ms,
            provider=self.provider,
            model=self.model,
            tool=self.tool,
            ok=self.ok,
            meta=self.meta,
        )
