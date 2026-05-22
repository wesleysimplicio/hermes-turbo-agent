"""Bootstrap the runtime ``$HERMES_TURBO_HOME`` directory from repo-local ``.hermes-turbo/`` defaults.

When an operator first runs Hermes Turbo Agent against a fresh ``$HERMES_TURBO_HOME``, this
module idempotently seeds the directory with the fork's opinionated defaults
shipped under the repo's ``.hermes-turbo/`` tree:

- ``HERMES_BASE`` — upstream Hermes baseline marker.
- ``version`` — Hermes Turbo version pin.
- ``memories/MEMORY.md`` — seed memory entries (Hermes Turbo identity, project-mapping
  directive, home resolution).
- ``mapped_projects.json`` — empty registry for the ``llm-project-mapper``
  skill.

Existing operator files are NEVER overwritten — the bootstrap is additive,
file-by-file, skip-if-exists. Each missing file is copied; each existing file
is left alone.

The bootstrap runs at most once per process and logs every action it takes (or
skips). Failures land in ``$HERMES_TURBO_HOME/logs/errors.log`` via the standard
logging setup and do not interrupt agent startup — the agent works fine
without the seed files, the operator just misses the curated defaults.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

_BOOTSTRAP_DONE: bool = False

# Files copied from `.hermes-turbo/` into the runtime home. Order doesn't matter
# (each file is independent), but the list is sorted to make the bootstrap
# log deterministic.
_BOOTSTRAP_FILES: tuple[str, ...] = (
    "HERMES_BASE",
    "mapped_projects.json",
    "memories/MEMORY.md",
    "version",
)


def _repo_root() -> Path:
    """Resolve the repo root (``.hermes-turbo/`` source) from this module's location."""
    return Path(__file__).resolve().parents[1]


def _source_dir() -> Path:
    """Locate the in-repo seed dir for the runtime home.

    Prefers ``.hermes-turbo/`` (canonical) and falls back to ``.tota/`` for
    repositories that haven't yet been migrated. The legacy fallback is
    deprecated and will be removed in a future release.
    """
    canonical = _repo_root() / ".hermes-turbo"
    if canonical.exists():
        return canonical
    legacy = _repo_root() / ".tota"
    if legacy.exists():
        return legacy
    return canonical


def bootstrap_hermes_turbo_home(force_reseed: bool = False) -> dict[str, str]:
    """Idempotently copy ``.hermes-turbo/`` defaults into the runtime ``$HERMES_TURBO_HOME``.

    Args:
        force_reseed: When True, also copy files that already exist in the
            runtime home (overwriting them). The default ``False`` preserves
            operator edits.

    Returns:
        ``{relative_path: status}`` mapping where ``status`` is one of
        ``"copied"``, ``"skipped-exists"``, ``"skipped-missing-source"``, or
        ``"error:<message>"``.
    """
    global _BOOTSTRAP_DONE
    if _BOOTSTRAP_DONE and not force_reseed:
        return {}

    source = _source_dir()
    if not source.is_dir():
        logger.debug("Hermes Turbo bootstrap: no .hermes-turbo/ source at %s, skipping.", source)
        _BOOTSTRAP_DONE = True
        return {}

    home = get_hermes_home()
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Hermes Turbo bootstrap: cannot create %s: %s", home, exc)
        return {"_home": f"error:{exc}"}

    results: dict[str, str] = {}
    for relpath in _BOOTSTRAP_FILES:
        src = source / relpath
        dst = home / relpath
        if not src.exists():
            results[relpath] = "skipped-missing-source"
            continue
        if dst.exists() and not force_reseed:
            results[relpath] = "skipped-exists"
            continue
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            results[relpath] = "copied"
            logger.info("Hermes Turbo bootstrap: copied %s -> %s", relpath, dst)
        except OSError as exc:
            results[relpath] = f"error:{exc}"
            logger.warning("Hermes Turbo bootstrap: failed to copy %s: %s", relpath, exc)

    _BOOTSTRAP_DONE = True
    return results


def reset_for_tests() -> None:
    """Reset the once-per-process guard. Test-only helper."""
    global _BOOTSTRAP_DONE
    _BOOTSTRAP_DONE = False
