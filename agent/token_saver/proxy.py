"""Native token-saver proxy for shell and tool output.

Wraps long command/tool output before it enters model context. Strategy is a
simple head/tail truncation at ``max_lines``: keep the first ``head`` lines and
the last ``tail`` lines, drop the middle, and persist the full payload to a
file. The caller receives the truncated text together with a handle string of
the form ``<handle:/abs/path/to/file>`` that can be used to fetch the full
output on demand.

The proxy is intentionally minimal -- it is the foundation for the broader
RTK-style command-aware adapters tracked in issue #88 (``git diff``, ``pytest``,
etc.). Adapters land in follow-up commits; this module nails the truncation and
handle contract first so they can build on top.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


DEFAULT_MAX_LINES = 200
DEFAULT_HEAD = 80
DEFAULT_TAIL = 80
_TRUNCATION_MARKER_PREFIX = "... [token-saver] truncated"


@dataclass
class TruncationResult:
    """Outcome of a single truncation pass."""

    text: str
    handle: Optional[str] = None
    full_path: Optional[str] = None
    original_line_count: int = 0
    kept_line_count: int = 0
    truncated: bool = False
    meta: dict = field(default_factory=dict)


def _format_handle(path: str) -> str:
    return f"<handle:{path}>"


def _persist_full(text: str, storage_dir: Path) -> str:
    storage_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(text.encode("utf-8", errors="replace")).hexdigest()[:12]
    timestamp = int(time.time() * 1000)
    target = storage_dir / f"output-{timestamp}-{digest}.txt"
    target.write_text(text, encoding="utf-8")
    return str(target)


def truncate_output(
    text: str,
    *,
    max_lines: int = DEFAULT_MAX_LINES,
    head: int = DEFAULT_HEAD,
    tail: int = DEFAULT_TAIL,
    storage_dir: Optional[Path] = None,
) -> TruncationResult:
    """Apply head/tail truncation to ``text``.

    - Returns the text unchanged when it has ``max_lines`` or fewer lines.
    - When truncated, persists the full payload to ``storage_dir`` (defaults to
      a stable subdirectory under the system temp dir) and returns a ``handle``
      pointing at the absolute path.
    - The visible payload contains the first ``head`` lines, a truncation
      marker reporting how many lines were elided, and the last ``tail`` lines.
    """
    if max_lines <= 0:
        raise ValueError("max_lines must be > 0")
    if head < 0 or tail < 0:
        raise ValueError("head and tail must be >= 0")
    if head + tail > max_lines:
        raise ValueError("head + tail must be <= max_lines")

    lines = text.splitlines()
    original_line_count = len(lines)

    if original_line_count <= max_lines:
        return TruncationResult(
            text=text,
            original_line_count=original_line_count,
            kept_line_count=original_line_count,
            truncated=False,
        )

    storage = storage_dir or Path(tempfile.gettempdir()) / "hermes-token-saver"
    full_path = _persist_full(text, storage)
    handle = _format_handle(full_path)

    head_slice = lines[:head] if head else []
    tail_slice = lines[-tail:] if tail else []
    elided = original_line_count - len(head_slice) - len(tail_slice)
    marker = (
        f"{_TRUNCATION_MARKER_PREFIX} {elided} lines "
        f"(full output: {handle})"
    )

    kept = head_slice + [marker] + tail_slice
    return TruncationResult(
        text="\n".join(kept),
        handle=handle,
        full_path=full_path,
        original_line_count=original_line_count,
        kept_line_count=len(head_slice) + len(tail_slice),
        truncated=True,
        meta={"head": len(head_slice), "tail": len(tail_slice), "elided": elided},
    )


class TokenSaverProxy:
    """Stateful wrapper that applies truncation to shell/tool outputs."""

    def __init__(
        self,
        *,
        max_lines: int = DEFAULT_MAX_LINES,
        head: int = DEFAULT_HEAD,
        tail: int = DEFAULT_TAIL,
        storage_dir: Optional[Path] = None,
    ) -> None:
        self.max_lines = max_lines
        self.head = head
        self.tail = tail
        self.storage_dir = (
            storage_dir or Path(tempfile.gettempdir()) / "hermes-token-saver"
        )

    def wrap(self, text: str) -> TruncationResult:
        return truncate_output(
            text,
            max_lines=self.max_lines,
            head=self.head,
            tail=self.tail,
            storage_dir=self.storage_dir,
        )

    def resolve(self, handle: str) -> str:
        """Read the full payload for a previously emitted ``handle``."""
        prefix = "<handle:"
        if not (handle.startswith(prefix) and handle.endswith(">")):
            raise ValueError(f"not a token-saver handle: {handle!r}")
        path = handle[len(prefix) : -1]
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        return Path(path).read_text(encoding="utf-8")
