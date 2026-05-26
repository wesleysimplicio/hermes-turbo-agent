"""Optional uvloop policy installer for Hermes async entrypoints."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

logger = logging.getLogger(__name__)

_INSTALLED = False


def install_uvloop_policy() -> bool:
    """Install uvloop when available and safe for the current platform."""
    global _INSTALLED
    if _INSTALLED:
        return True
    if sys.platform == "win32" or os.getenv("HERMES_DISABLE_UVLOOP") == "1":
        return False

    try:
        import uvloop  # type: ignore
    except ImportError:
        return False

    current_policy = asyncio.get_event_loop_policy()
    if isinstance(current_policy, uvloop.EventLoopPolicy):
        _INSTALLED = True
        return True

    try:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
    except RuntimeError as exc:
        logger.debug("uvloop policy was not installed: %s", exc)
        return False

    _INSTALLED = True
    return True
