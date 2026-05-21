"""RTK compatibility bridge.

Optional bridge for the RTK token-saver CLI (https://github.com/rtk-ai/rtk).
If `rtk` is on PATH, shell commands can be routed through `rtk <cmd>`;
otherwise the plain command is returned unchanged.

Backends:
- ``native``: never use rtk, return argv as-is.
- ``rtk``: always wrap with rtk; raise if rtk is missing.
- ``auto`` (default): wrap with rtk when detected and the command is in the
  compatibility allow-list, otherwise fall through.

Backend is selected via the ``HERMES_TOKEN_SAVER`` env var.
"""

from __future__ import annotations

import os
import shutil
from typing import Iterable, List, Sequence

BACKEND_NATIVE = "native"
BACKEND_RTK = "rtk"
BACKEND_AUTO = "auto"
VALID_BACKENDS = frozenset({BACKEND_NATIVE, BACKEND_RTK, BACKEND_AUTO})

ENV_BACKEND = "HERMES_TOKEN_SAVER"

# Commands RTK accepts as a direct prefix; anything else falls through.
RTK_COMPATIBLE_COMMANDS = frozenset(
    {"read", "grep", "find", "git", "npx", "ls", "cat", "head", "tail"}
)


class RtkNotInstalledError(RuntimeError):
    """Raised when backend=rtk is requested but the binary is missing."""


def is_rtk_available() -> bool:
    return shutil.which("rtk") is not None


def resolve_backend(requested: str | None = None) -> str:
    candidate = (requested or os.environ.get(ENV_BACKEND) or BACKEND_AUTO).strip().lower()
    return candidate if candidate in VALID_BACKENDS else BACKEND_AUTO


def wrap_command(argv: Sequence[str], backend: str | None = None) -> List[str]:
    """Transform ``argv`` according to the active backend. Never executes."""
    if not argv:
        return []
    argv_list = [str(a) for a in argv]
    mode = resolve_backend(backend)

    if mode == BACKEND_NATIVE:
        return argv_list
    if mode == BACKEND_RTK:
        if not is_rtk_available():
            raise RtkNotInstalledError(
                "HERMES_TOKEN_SAVER=rtk but `rtk` was not found on PATH. "
                "Install https://github.com/rtk-ai/rtk or switch to native/auto."
            )
        return ["rtk", *argv_list]
    # auto
    if is_rtk_available() and argv_list[0] in RTK_COMPATIBLE_COMMANDS:
        return ["rtk", *argv_list]
    return argv_list


def describe() -> dict:
    backend = resolve_backend()
    available = is_rtk_available()
    effective = (
        BACKEND_RTK
        if (backend == BACKEND_RTK or (backend == BACKEND_AUTO and available))
        else BACKEND_NATIVE
    )
    return {
        "backend": backend,
        "rtk_available": available,
        "rtk_path": shutil.which("rtk"),
        "effective": effective,
    }


def iter_compatible_commands() -> Iterable[str]:
    return iter(sorted(RTK_COMPATIBLE_COMMANDS))


__all__ = [
    "BACKEND_AUTO",
    "BACKEND_NATIVE",
    "BACKEND_RTK",
    "ENV_BACKEND",
    "RTK_COMPATIBLE_COMMANDS",
    "RtkNotInstalledError",
    "VALID_BACKENDS",
    "describe",
    "is_rtk_available",
    "iter_compatible_commands",
    "resolve_backend",
    "wrap_command",
]
