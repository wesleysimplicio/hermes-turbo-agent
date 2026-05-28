"""Optional simplicio-prompt message preparation."""

from __future__ import annotations

import os
from typing import Any, Dict, List

MARKER = "<!-- simplicio-prompt:hermes-turbo -->"
_TRUE = {"1", "true", "yes", "on"}

_TEXT = (
    "Use simplicio-prompt before answering. Treat the request as an "
    "addressable yool, identify the deliverable and checks internally, "
    "then return one concrete verified result."
)
_BATCH_TEXT = (
    "Use simplicio-prompt batch mode for parallel work. Split independent "
    "yool tuples, keep bounded lanes, merge receipts, and return one result."
)


def _enabled() -> bool:
    raw = os.environ.get("HERMES_SIMPLICIO_PROMPT") or os.environ.get("SIMPLICIO_PROMPT")
    if raw is None:
        raw = os.environ.get("YOOL_TUPLE_FULL_RUNTIME")
    return str(raw or "").strip().lower() in _TRUE


def _block() -> str:
    batch = str(os.environ.get("YOOL_TUPLE_FULL_RUNTIME") or "").strip().lower() in _TRUE
    text = _BATCH_TEXT if batch else _TEXT
    return f"{MARKER}\n# simplicio-prompt\n\n{text}"


def _has_marker(content: Any) -> bool:
    if isinstance(content, str):
        return MARKER in content
    if isinstance(content, list):
        return any(isinstance(item, dict) and MARKER in str(item.get("text") or item.get("content") or "") for item in content)
    return False


def apply_simplicio_prompt(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not _enabled() or not isinstance(messages, list):
        return messages
    if any(isinstance(msg, dict) and msg.get("role") in {"system", "developer"} and _has_marker(msg.get("content")) for msg in messages):
        return messages
    block = _block()
    cloned = [dict(msg) if isinstance(msg, dict) else msg for msg in messages]
    if cloned and isinstance(cloned[0], dict) and cloned[0].get("role") in {"system", "developer"}:
        first = dict(cloned[0])
        content = first.get("content")
        if isinstance(content, list):
            first["content"] = [*content, {"type": "text", "text": block}]
        else:
            text = str(content or "").rstrip()
            first["content"] = f"{text}\n\n{block}" if text else block
        cloned[0] = first
        return cloned
    return [{"role": "system", "content": block}, *cloned]
