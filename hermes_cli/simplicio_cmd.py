"""``hermes simplicio`` — run the vendored simplicio 6-layer task→code contract.

This is a thin passthrough to :mod:`simplicio.cli`. Everything after the
``simplicio`` token on the command line is forwarded verbatim, so::

    hermes simplicio task "hide Delete for non-admins" --target a.html
    hermes simplicio index --stack angular
    hermes simplicio smoke
    hermes simplicio bench --cases bench/cases.json

behave exactly like the standalone ``simplicio`` console script.

The ``index``/``task``/``bench`` subcommands rank repo precedent with an
embedding model, so we best-effort ensure the optional ``simplicio.embeddings``
feature (numpy + sentence-transformers) before delegating. ``smoke`` and
``--help`` don't need it. If the embedding stack can't be installed (offline,
lazy installs disabled) we still delegate — the user gets the precise pip hint
from :class:`tools.lazy_deps.FeatureUnavailable` rather than a bare traceback.
"""

from __future__ import annotations

import sys

# Subcommands that perform embedding-backed precedent ranking.
_NEEDS_EMBEDDINGS = frozenset({"index", "task", "bench"})


def _maybe_ensure_embeddings(simplicio_args: list[str]) -> None:
    if "-h" in simplicio_args or "--help" in simplicio_args:
        return  # help text needs nothing — don't trigger an install
    sub = next((a for a in simplicio_args if not a.startswith("-")), None)
    if sub not in _NEEDS_EMBEDDINGS:
        return
    try:
        from tools.lazy_deps import FeatureUnavailable, ensure
    except Exception:
        return
    try:
        ensure("simplicio.embeddings")
    except FeatureUnavailable as exc:
        # Surface the actionable install hint, then let simplicio raise the
        # concrete ImportError at the point of use.
        print(f"[simplicio] {exc}", file=sys.stderr)


def run_simplicio(simplicio_args: list[str]) -> int:
    """Forward ``simplicio_args`` to :func:`simplicio.cli.main`."""
    from simplicio.cli import main as simplicio_main

    _maybe_ensure_embeddings(simplicio_args)

    saved = sys.argv
    sys.argv = ["simplicio", *simplicio_args]
    try:
        simplicio_main()
        return 0
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        if isinstance(code, int):
            return code
        print(str(code), file=sys.stderr)
        return 1
    finally:
        sys.argv = saved


__all__ = ["run_simplicio"]
