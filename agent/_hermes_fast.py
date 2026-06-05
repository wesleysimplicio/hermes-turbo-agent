"""Optional Rust hot-path bridge.

Phase 3 (perf): thin Python wrapper around the ``hermes_fast`` PyO3
extension built by ``rust_ext/``. When the compiled extension is
unavailable (no Rust toolchain, Termux, source-only install) we fall
back to pure-Python implementations that match existing agent semantics
exactly, so the fallback path is a drop-in replacement.

Dispatch policy (measured 2026-06, varied sizes, best-of-5):

- ``parse_tool_call_delta`` is routed through Rust whenever the
  extension is present — its input is already a string and the work is
  real JSON parsing, so Rust wins **~3x** with no marshalling tax.
- ``estimate_tokens`` / ``estimate_tokens_many`` /
  ``estimate_messages_tokens`` / ``truncate_messages_to_limit`` default
  to **pure Python**, even when the extension is present. Those ops are
  dominated by the ``_fast_dumps_bytes`` JSON-serialize + FFI boundary
  crossing they must do *before* Rust can touch the data; that overhead
  swamps the trivial ``(len+3)//4`` arithmetic, so Python is reliably
  1.1-1.5x faster (and the gap widens with batch size). Set
  ``HERMES_RUST_ESTIMATES=1`` to force the Rust path for these if a
  future extension build changes the trade-off (e.g. a zero-copy API
  that no longer needs the pre-serialization pass).

Build the extension with::

    cd rust_ext && maturin develop --release

``HAVE_RUST`` reports whether the extension is loaded; it does not by
itself mean estimation runs in Rust (see policy above).
"""

from __future__ import annotations

import json
import os
from typing import Any, Iterable

from agent._fastjson import _fast_dumps, _fast_dumps_bytes, _fast_loads

try:
    import hermes_fast as _rust  # type: ignore

    HAVE_RUST = True
except ImportError:  # pragma: no cover - fallback path
    _rust = None  # type: ignore
    HAVE_RUST = False

# Opt-in override: route estimation/truncation through Rust despite the
# measured boundary-cost penalty. Off by default — see the module docstring.
_USE_RUST_ESTIMATES = os.getenv("HERMES_RUST_ESTIMATES") == "1"


def _rust_estimates_active() -> bool:
    """True only when the extension is loaded AND the opt-in flag is set."""
    return _rust is not None and _USE_RUST_ESTIMATES


def parse_tool_call_delta(buf: str) -> tuple[bool, Any, int]:
    """Try to parse a JSON value from ``buf``.

    Returns ``(ok, value_or_none, consumed_bytes)``. ``ok`` is ``False``
    when the buffer is empty / incomplete; the caller should append more
    bytes and retry. Trailing bytes past the first complete value are
    left untouched.
    """
    if _rust is not None:
        return _rust.parse_tool_call_delta(buf)  # type: ignore[attr-defined]

    trimmed = buf.lstrip()
    if not trimmed:
        return (False, None, 0)
    leading = len(buf) - len(trimmed)
    decoder = json.JSONDecoder()
    try:
        value, end = decoder.raw_decode(trimmed)
    except json.JSONDecodeError:
        return (False, None, 0)
    return (True, value, leading + end)


def estimate_tokens(text: str) -> int:
    """~4 chars/token heuristic. Empty => 0. Else ceil(len/4)."""
    if _rust_estimates_active():
        return _rust.estimate_tokens(text)  # type: ignore[attr-defined]
    if not text:
        return 0
    return (len(text) + 3) // 4


def _estimate_tokens_local(text: str) -> int:
    if not text:
        return 0
    return (len(text) + 3) // 4


def estimate_tokens_many(texts: Iterable[str]) -> list[int]:
    """Estimate many strings with one Rust boundary crossing when available."""
    text_list = [text if isinstance(text, str) else str(text) for text in texts]
    if _rust_estimates_active():
        return list(_rust.estimate_tokens_many(text_list))  # type: ignore[attr-defined]
    return [_estimate_tokens_local(text) for text in text_list]


def _py_message_cost(msg: dict[str, Any]) -> int:
    role = msg.get("role", "")
    content = msg.get("content")
    role_t = _estimate_tokens_local(role) if isinstance(role, str) else 0
    if isinstance(content, str):
        content_t = _estimate_tokens_local(content)
    elif isinstance(content, list):
        content_t = 0
        for item in content:
            if isinstance(item, str):
                content_t += _estimate_tokens_local(item)
            elif isinstance(item, dict):
                for v in item.values():
                    if isinstance(v, str):
                        content_t += _estimate_tokens_local(v)
                    else:
                        content_t += _estimate_tokens_local(_fast_dumps(v, ensure_ascii=False))
            else:
                content_t += _estimate_tokens_local(_fast_dumps(item, ensure_ascii=False))
    elif content is None:
        content_t = 0
    else:
        content_t = _estimate_tokens_local(_fast_dumps(content, ensure_ascii=False))
    return role_t + content_t + 4


def estimate_messages_tokens(messages: Iterable[dict[str, Any]]) -> int:
    """Estimate the total token budget for OpenAI-style message dicts."""
    msg_list = list(messages)
    if _rust_estimates_active():
        encoded = _fast_dumps_bytes(msg_list, ensure_ascii=False)
        if hasattr(_rust, "estimate_messages_tokens_bytes"):
            return int(_rust.estimate_messages_tokens_bytes(encoded))  # type: ignore[attr-defined]
        return int(_rust.estimate_messages_tokens(encoded.decode("utf-8")))  # type: ignore[attr-defined]
    return sum(_py_message_cost(m) for m in msg_list)


def truncate_messages_to_limit(
    messages: Iterable[dict[str, Any]], max_tokens: int
) -> list[dict[str, Any]]:
    """Drop oldest non-system messages until total estimate <= ``max_tokens``.

    Accepts a Python list (or any iterable) of ``{"role": ..., "content": ...}``
    dicts. Returns a new list. System messages are preserved.
    """
    msg_list = list(messages)
    if _rust_estimates_active():
        encoded = _fast_dumps_bytes(msg_list, ensure_ascii=False)
        if hasattr(_rust, "truncate_messages_to_limit_bytes"):
            out = _rust.truncate_messages_to_limit_bytes(encoded, int(max_tokens))  # type: ignore[attr-defined]
        else:
            out = _rust.truncate_messages_to_limit(encoded.decode("utf-8"), int(max_tokens))  # type: ignore[attr-defined]
        return _fast_loads(out)

    costs = [_py_message_cost(m) for m in msg_list]
    total = sum(costs)
    if total <= max_tokens:
        return msg_list

    i = 0
    while total > max_tokens and i < len(msg_list):
        if msg_list[i].get("role") == "system":
            i += 1
            continue
        total -= costs[i]
        del msg_list[i]
        del costs[i]
    return msg_list


__all__ = [
    "HAVE_RUST",
    "estimate_tokens",
    "estimate_tokens_many",
    "estimate_messages_tokens",
    "parse_tool_call_delta",
    "truncate_messages_to_limit",
]
