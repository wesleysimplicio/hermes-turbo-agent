"""Bootstrap the runtime ``$TOTA_HOME`` directory from repo-local ``.tota/`` defaults.

When an operator first runs Tota Agent against a fresh ``$TOTA_HOME``, this
module idempotently seeds the directory with the fork's opinionated defaults
shipped under the repo's ``.tota/`` tree:

- ``HERMES_BASE`` — upstream Hermes baseline marker.
- ``version`` — Tota version pin.
- ``memories/MEMORY.md`` — seed memory entries (Tota identity, project-mapping
  directive, home resolution).
- ``mapped_projects.json`` — empty registry for the ``llm-project-mapper``
  skill.

Existing operator files are NEVER overwritten — the bootstrap is additive,
file-by-file, skip-if-exists. Each missing file is copied; each existing file
is left alone.

The bootstrap runs at most once per process and logs every action it takes (or
skips). Failures land in ``$TOTA_HOME/logs/errors.log`` via the standard
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

# Files copied from `.tota/` into the runtime home. Order doesn't matter
# (each file is independent), but the list is sorted to make the bootstrap
# log deterministic.
_BOOTSTRAP_FILES: tuple[str, ...] = (
    "HERMES_BASE",
    "mapped_projects.json",
    "memories/MEMORY.md",
    "version",
)


def _repo_root() -> Path:
    """Resolve the repo root (``.tota/`` source) from this module's location."""
    return Path(__file__).resolve().parents[1]


def _source_dir() -> Path:
    return _repo_root() / ".tota"


def bootstrap_tota_home(force_reseed: bool = False) -> dict[str, str]:
    """Idempotently copy ``.tota/`` defaults into the runtime ``$TOTA_HOME``.

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
        logger.debug("Tota bootstrap: no .tota/ source at %s, skipping.", source)
        _BOOTSTRAP_DONE = True
        return {}

    home = get_hermes_home()
    try:
        home.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning("Tota bootstrap: cannot create %s: %s", home, exc)
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
            logger.info("Tota bootstrap: copied %s -> %s", relpath, dst)
        except OSError as exc:
            results[relpath] = f"error:{exc}"
            logger.warning("Tota bootstrap: failed to copy %s: %s", relpath, exc)

    _BOOTSTRAP_DONE = True
    return results


def reset_for_tests() -> None:
    """Reset the once-per-process guard. Test-only helper."""
    global _BOOTSTRAP_DONE
    _BOOTSTRAP_DONE = False
