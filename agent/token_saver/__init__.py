"""Hermes Turbo native token-saver proxy.

Provides command/tool output compression before content enters model context.
See ``proxy`` for the head/tail truncation strategy and file-backed handles.
"""

from agent.token_saver.backend import (
    BackendChoice,
    BackendDecision,
    BackendError,
    detect_rtk,
    resolve_backend,
    saver,
)
from agent.token_saver.proxy import (
    TokenSaverProxy,
    TruncationResult,
    truncate_output,
)

__all__ = [
    "BackendChoice",
    "BackendDecision",
    "BackendError",
    "TokenSaverProxy",
    "TruncationResult",
    "detect_rtk",
    "resolve_backend",
    "saver",
    "truncate_output",
]
