"""Hermes Turbo native token-saver proxy.

Provides command/tool output compression before content enters model context.
See ``proxy`` for the head/tail truncation strategy and file-backed handles.
"""

from agent.token_saver.proxy import (
    TokenSaverProxy,
    TruncationResult,
    truncate_output,
)

__all__ = ["TokenSaverProxy", "TruncationResult", "truncate_output"]
