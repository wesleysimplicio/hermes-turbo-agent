"""Auto-invoke ``llm-project-mapper`` on first turn in a code project.

This is the runtime side of the Hermes Turbo-core directive in
``DEFAULT_AGENT_IDENTITY``. When Hermes Turbo Agent enters a project that looks like
code (has a ``.git`` directory, ``pyproject.toml``, ``package.json``, etc.),
this module spawns ``skills/software-development/llm-project-mapper/scripts/map_project.py``
once per session, idempotently, so the project ships with the AGENTS.md
ecosystem the agent (and every downstream tool) needs to operate without
re-onboarding.

Detection heuristics — any one is enough to qualify as a code project:

- ``.git`` directory (real git repo or worktree gitfile)
- ``pyproject.toml`` / ``package.json`` / ``Cargo.toml`` / ``go.mod`` / ``pom.xml``
- ``CMakeLists.txt`` / ``Makefile`` / ``Gemfile`` / ``composer.json``

Skip conditions (any one disables the auto-trigger):

- ``HERMES_TURBO_AUTO_MAP=0`` (or ``TOTA_AUTO_MAP=0`` legacy, or ``HERMES_AUTO_MAP=0``) in env.
- ``$HERMES_TURBO_HOME/.disable_auto_mapper`` sentinel file exists.
- cwd is the user's home directory itself.
- cwd is the Hermes Turbo Agent repo (avoid Hermes Turbo mapping its own source).
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

from hermes_constants import get_hermes_home

logger = logging.getLogger(__name__)

_AUTO_MAP_DONE: set[Path] = set()

_CODE_PROJECT_MARKERS: tuple[str, ...] = (
    ".git",
    "pyproject.toml",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "CMakeLists.txt",
    "Makefile",
    "Gemfile",
    "composer.json",
)


def _is_disabled() -> bool:
    for key in ("HERMES_TURBO_AUTO_MAP", "TOTA_AUTO_MAP", "HERMES_AUTO_MAP"):
        val = os.environ.get(key, "").strip().lower()
        if val in {"0", "false", "no", "off"}:
            return True
    try:
        sentinel = get_hermes_home() / ".disable_auto_mapper"
        if sentinel.exists():
            return True
    except Exception:
        pass
    return False


def _is_code_project(project_root: Path) -> bool:
    return any((project_root / marker).exists() for marker in _CODE_PROJECT_MARKERS)


def _is_own_repo(project_root: Path) -> bool:
    """Return True when the cwd IS the Hermes Turbo Agent repo itself.

    Mapping our own source on every CLI invocation is annoying and not what
    operators want.  We detect by checking for the ``.hermes-turbo/HERMES_BASE``
    marker (canonical) or the legacy ``.tota/HERMES_BASE`` marker from before
    the 0.15.0 rebrand.
    """
    if (project_root / ".hermes-turbo" / "HERMES_BASE").exists():
        return True
    return (project_root / ".tota" / "HERMES_BASE").exists()


def _is_home_dir(project_root: Path) -> bool:
    try:
        return project_root.resolve() == Path.home().resolve()
    except (OSError, RuntimeError):
        return False


def _mapper_script() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "skills"
        / "software-development"
        / "llm-project-mapper"
        / "scripts"
        / "map_project.py"
    )


def maybe_map_project(cwd: str | Path | None = None) -> dict[str, object]:
    """Run the mapper on ``cwd`` when conditions warrant.

    Returns a status dict:
        ``{"ran": bool, "reason": str, "result": dict | None}``

    ``ran=True`` means the mapper script was actually spawned. ``ran=False``
    with ``reason`` describing why: ``"disabled"``, ``"not-code-project"``,
    ``"own-repo"``, ``"home-dir"``, ``"already-mapped-this-session"``,
    ``"mapper-missing"``.
    """
    project_root = Path(cwd) if cwd is not None else Path.cwd()
    try:
        project_root = project_root.resolve()
    except OSError as exc:
        return {"ran": False, "reason": f"resolve-error:{exc}", "result": None}

    if _is_disabled():
        return {"ran": False, "reason": "disabled", "result": None}
    if project_root in _AUTO_MAP_DONE:
        return {"ran": False, "reason": "already-mapped-this-session", "result": None}
    if _is_own_repo(project_root):
        _AUTO_MAP_DONE.add(project_root)
        return {"ran": False, "reason": "own-repo", "result": None}
    if _is_home_dir(project_root):
        return {"ran": False, "reason": "home-dir", "result": None}
    if not _is_code_project(project_root):
        return {"ran": False, "reason": "not-code-project", "result": None}

    script = _mapper_script()
    if not script.exists():
        return {"ran": False, "reason": "mapper-missing", "result": None}

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--project-root", str(project_root)],
            capture_output=True,
            text=True,
            check=False,
            timeout=900,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("Auto-mapper subprocess failed: %s", exc)
        return {"ran": False, "reason": f"spawn-error:{exc}", "result": None}

    parsed: dict | None = None
    if result.stdout:
        try:
            import json

            parsed = json.loads(result.stdout)
        except (ValueError, TypeError):
            parsed = None

    # Only mark this project as "done for the session" if the mapper actually
    # succeeded.  A non-zero exit or an ``ok: false`` payload means the next
    # invocation within the same process should try again instead of silently
    # skipping.  Closes Copilot review on PR #61.
    success = result.returncode == 0 and (
        parsed is None or parsed.get("ok") is True
    )
    if success:
        _AUTO_MAP_DONE.add(project_root)
        reason = "mapped"
    else:
        reason = f"mapper-failed:returncode={result.returncode}"
        if parsed and parsed.get("error"):
            reason = f"mapper-failed:{parsed['error']}"
        logger.warning(
            "Auto-mapper failed for %s: returncode=%s, parsed=%r",
            project_root,
            result.returncode,
            parsed,
        )

    return {
        "ran": True,
        "reason": reason,
        "result": parsed,
        "returncode": result.returncode,
        "ok": success,
    }


def reset_for_tests() -> None:
    """Clear the per-session dedup set. Test-only helper."""
    _AUTO_MAP_DONE.clear()
