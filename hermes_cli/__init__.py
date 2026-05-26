"""
Hermes CLI - Unified command-line interface for Hermes Agent.

Provides subcommands for:
- hermes chat          - Interactive chat (same as ./hermes)
- hermes gateway       - Run gateway in foreground
- hermes gateway start - Start gateway service
- hermes gateway stop  - Stop gateway service
- hermes setup         - Interactive setup wizard
- hermes status        - Show status of all components
- hermes cron          - Manage cron jobs
"""

import os
import sys

__version__ = "0.15.1"
__release_date__ = "2026.5.25"

_MIN_PYTHON = (3, 11)


def _assert_python_version(current=None, min_version=_MIN_PYTHON, exit_fn=sys.exit):
    """Fail fast with a friendly message on unsupported Python versions.

    The package uses 3.10+ syntax (`X | None`) that raises an opaque
    TypeError on import under older interpreters. Surface a clear error.
    """
    info = current if current is not None else sys.version_info
    if tuple(info[:2]) < min_version:
        running = ".".join(str(p) for p in info[:3])
        required = ".".join(str(p) for p in min_version)
        sys.stderr.write(
            "hermes-agent requires Python "
            + required
            + "+ (found "
            + running
            + ").\nInstall Python "
            + required
            + " or newer and re-run.\n"
        )
        return exit_fn(1)
    return None


_assert_python_version()


def _ensure_utf8():
    """Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError.

    Windows services and terminals default to cp1252, which cannot encode
    box-drawing characters used in CLI output. This causes unhandled
    UnicodeEncodeError crashes on gateway startup.
    """
    if sys.platform != "win32":
        return
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            if getattr(stream, "encoding", "").lower().replace("-", "") != "utf8":
                new_stream = open(
                    stream.fileno(), "w", encoding="utf-8",
                    buffering=1, closefd=False,
                )
                setattr(sys, stream_name, new_stream)
        except (AttributeError, OSError):
            pass


_ensure_utf8()
