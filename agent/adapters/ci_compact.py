"""Token-optimized CI log parser.

Reads raw GitHub Actions / generic CI log text and returns only the
failing stages plus a short first-error excerpt per stage. Designed to
turn megabytes of `gh run view --log` output into a handful of lines.
Stdlib-only.

Refs #90.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# GitHub Actions log line shape:
#   <Job>\t<step>\t<timestamp> <message>
# We are intentionally permissive — we accept either tab-delimited GHA
# output or plain log lines from any CI.
_GHA_LINE = re.compile(
    r"^(?P<job>[^\t]+)\t(?P<step>[^\t]+)\t"
    r"(?P<ts>\S+)\s+(?P<msg>.*)$"
)

_ERROR_MARKERS = re.compile(
    r"(?i)\b(error|fatal|failed|failure|traceback|exception|panic|assert(ion)?)\b"
    r"|^##\[error\]|^E\s+|^\s*FAIL\b"
)

# Higher-signal markers — used to upgrade the chosen signature when the
# first match is a low-signal line like "test_bar FAILED".
_STRONG_MARKERS = re.compile(
    r"(?i)^##\[error\]|^E\s+|\b(traceback|assert(ion)?error|exception|panic|fatal)\b"
)

_NOISE_PREFIXES = (
    "##[group]",
    "##[endgroup]",
    "##[debug]",
    "::group::",
    "::endgroup::",
    "::debug::",
)

_PROGRESS_PATTERNS = re.compile(
    r"^\s*(Downloading|Receiving objects|Resolving deltas|"
    r"\[\d+/\d+\]|Progress:|\d+%\s)"
)

_EXCERPT_LINES = 5


def _strip_ts(line: str) -> str:
    """Strip a leading ISO timestamp like `2024-05-20T12:34:56.789Z `."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z?\s+", "", line)


def _is_noise(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if stripped.startswith(_NOISE_PREFIXES):
        return True
    if _PROGRESS_PATTERNS.match(stripped):
        return True
    return False


def _parse_line(line: str) -> Tuple[Optional[str], Optional[str], str]:
    """Return (job, step, message). Job/step are None for non-GHA lines."""
    m = _GHA_LINE.match(line)
    if m:
        return m.group("job"), m.group("step"), m.group("msg")
    return None, None, _strip_ts(line)


def parse_ci_log(text: str) -> Dict[str, Any]:
    """Group a CI log by (job, step) and return failing stages only.

    Returns a dict shaped like::

        {
            "failing": [
                {
                    "job": "build",
                    "step": "pytest",
                    "first_error_line": 142,
                    "excerpt": "...\\n...",
                    "signature": "AssertionError: expected 1 got 2",
                }
            ],
            "stats": {"total_lines": 4321, "stages_seen": 7, "stages_failing": 1},
        }
    """
    lines = text.splitlines()
    stages: Dict[Tuple[Optional[str], Optional[str]], Dict[str, Any]] = {}

    for idx, raw in enumerate(lines, start=1):
        if _is_noise(raw):
            continue
        job, step, msg = _parse_line(raw)
        key = (job, step)
        stage = stages.setdefault(key, {
            "job": job,
            "step": step,
            "first_error_line": None,
            "error_lines": [],
            "signature": None,
        })
        if _ERROR_MARKERS.search(msg):
            if stage["first_error_line"] is None:
                stage["first_error_line"] = idx
                stage["signature"] = _first_signature(msg)
            elif _STRONG_MARKERS.search(msg) and not _STRONG_MARKERS.search(
                stage["signature"] or ""
            ):
                # Upgrade a weak signature ("test_x FAILED") to a strong one.
                stage["signature"] = _first_signature(msg)
            if len(stage["error_lines"]) < _EXCERPT_LINES:
                stage["error_lines"].append(msg.rstrip())

    failing = []
    for stage in stages.values():
        if stage["first_error_line"] is None:
            continue
        failing.append({
            "job": stage["job"],
            "step": stage["step"],
            "first_error_line": stage["first_error_line"],
            "excerpt": "\n".join(stage["error_lines"]),
            "signature": stage["signature"],
        })

    return {
        "failing": failing,
        "stats": {
            "total_lines": len(lines),
            "stages_seen": len(stages),
            "stages_failing": len(failing),
        },
    }


def _first_signature(msg: str) -> str:
    """Best-effort short signature: the bit after the first marker."""
    cleaned = msg.strip()
    cleaned = re.sub(r"^##\[error\]\s*", "", cleaned)
    cleaned = re.sub(r"^E\s+", "", cleaned)
    return cleaned[:160]


def summarize_runs(runs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compact `gh run list --json ...` output, keeping only failing runs."""
    out = []
    for r in runs:
        conclusion = (r.get("conclusion") or "").lower()
        status = (r.get("status") or "").lower()
        if conclusion in {"success", "skipped", "neutral"}:
            continue
        if not conclusion and status in {"", "completed"}:
            continue
        out.append({
            "id": r.get("databaseId") or r.get("id"),
            "name": r.get("name") or r.get("workflowName"),
            "conclusion": conclusion or r.get("status"),
            "headBranch": r.get("headBranch"),
            "url": r.get("url"),
            "createdAt": r.get("createdAt"),
        })
    return out
