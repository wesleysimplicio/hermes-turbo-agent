"""Token-saver backend selector (native | rtk | auto).

External tool support: when ``rtk`` (https://github.com/rtk-ai/rtk) is on
PATH the agent can route compression-friendly shell commands through it
instead of relying solely on the native :mod:`agent.token_saver.proxy`.
The default is ``auto`` — use rtk when available, fall back to native.

Configuration:
    Env ``HERMES_TOKEN_SAVER_BACKEND`` -- one of ``native``, ``rtk``, ``auto``.

Resolution rules (see ``docs/perf/token-saver-proxy.md``):
    * ``native`` -- always use :func:`truncate_output` from the proxy.
    * ``rtk``    -- require ``rtk`` on PATH; if missing, ``BackendError``.
    * ``auto``   -- prefer ``rtk`` when available, otherwise native.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional, Sequence

from agent.token_saver.proxy import TruncationResult, truncate_output

ENV_BACKEND = "HERMES_TOKEN_SAVER_BACKEND"


class BackendChoice(str, Enum):
    NATIVE = "native"
    RTK = "rtk"
    AUTO = "auto"


class BackendError(RuntimeError):
    """Raised when the requested backend cannot be satisfied."""


@dataclass(frozen=True)
class BackendDecision:
    requested: BackendChoice
    chosen: BackendChoice  # never AUTO -- resolved
    rtk_available: bool
    rtk_path: Optional[str]

    @property
    def is_native(self) -> bool:
        return self.chosen is BackendChoice.NATIVE


def _which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def detect_rtk(binary: str = "rtk") -> Optional[str]:
    """Return absolute path to ``rtk`` if installed, else ``None``."""
    return _which(binary)


def _parse_choice(value: Optional[str]) -> BackendChoice:
    if not value:
        return BackendChoice.AUTO
    cleaned = value.strip().lower()
    try:
        return BackendChoice(cleaned)
    except ValueError as exc:
        raise BackendError(
            f"invalid {ENV_BACKEND}={value!r}; expected one of {[c.value for c in BackendChoice]}"
        ) from exc


def resolve_backend(
    requested: Optional[str] = None, *, rtk_binary: str = "rtk"
) -> BackendDecision:
    """Resolve ``native|rtk|auto`` -> concrete ``native|rtk`` decision."""
    if requested is None:
        requested = os.environ.get(ENV_BACKEND)
    choice = _parse_choice(requested)
    rtk_path = detect_rtk(rtk_binary)
    if choice is BackendChoice.NATIVE:
        return BackendDecision(choice, BackendChoice.NATIVE, rtk_path is not None, rtk_path)
    if choice is BackendChoice.RTK:
        if rtk_path is None:
            raise BackendError(
                f"backend=rtk requested but {rtk_binary!r} is not on PATH"
            )
        return BackendDecision(choice, BackendChoice.RTK, True, rtk_path)
    # AUTO: prefer rtk, fallback native.
    chosen = BackendChoice.RTK if rtk_path else BackendChoice.NATIVE
    return BackendDecision(choice, chosen, rtk_path is not None, rtk_path)


def compress_with_rtk(
    text: str, *, rtk_path: str, hint: Optional[str] = None, timeout_s: float = 5.0
) -> Optional[str]:
    """Pipe ``text`` through ``rtk`` and return its compressed stdout.

    Returns ``None`` on failure so the caller can fall back to native. The
    function never raises into the agent loop -- token saving is best-effort.
    """
    args: Sequence[str] = [rtk_path, "compress"] + (["--hint", hint] if hint else [])
    try:
        proc = subprocess.run(  # noqa: S603 -- explicit args, no shell
            list(args),
            input=text,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def saver(
    text: str,
    *,
    hint: Optional[str] = None,
    storage_dir: Optional[Path] = None,
    backend: Optional[str] = None,
) -> TruncationResult:
    """Compress ``text`` using the resolved backend.

    Always returns a :class:`TruncationResult`. When rtk is chosen but fails,
    the native proxy is used so the agent never sees a partial state.
    """
    decision = resolve_backend(backend)
    if decision.chosen is BackendChoice.RTK and decision.rtk_path:
        compressed = compress_with_rtk(text, rtk_path=decision.rtk_path, hint=hint)
        if compressed is not None and compressed != text:
            kept = compressed.splitlines()
            original_lines = text.splitlines()
            return TruncationResult(
                text=compressed,
                handle=None,
                full_path=None,
                original_line_count=len(original_lines),
                kept_line_count=len(kept),
                truncated=len(kept) < len(original_lines),
                meta={"backend": "rtk", "hint": hint or ""},
            )
    return truncate_output(text, storage_dir=storage_dir)
