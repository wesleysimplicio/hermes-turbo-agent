#!/usr/bin/env python3
"""Map a code project with @wesleysimplicio/llm-project-mapper.

Hermes Turbo Agent treats project mapping as a core onboarding step. This script is
idempotent: re-running on an already-mapped project is a no-op unless
``--force`` is passed.

Memory lives in ``$TOTA_HOME/mapped_projects.json`` (falling back to
``$HERMES_HOME``, then ``~/.hermes_turbo``) so mapping survives across sessions and
profiles.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


MAPPER_NPM_PACKAGE = "@wesleysimplicio/llm-project-mapper"
MEMORY_FILENAME = "mapped_projects.json"
DEFAULT_TTL_DAYS = 30

# Artifacts the mapper writes on a successful run.  Used by ``_ralph_ready``
# to confirm the mapping actually produced the AGENTS.md ecosystem instead
# of just dropping AGENTS.md.  Kept in sync with the mapper's bin/cli.js
# copy list (AGENTS.md, CLAUDE.md, INIT.md, _BOOTSTRAP.md).
_RALPH_MIN_ARTIFACTS = ("AGENTS.md", "INIT.md", "_BOOTSTRAP.md")
_MAPPER_VERSION_RE = re.compile(r"v(\d+\.\d+\.\d+(?:[-+][\w.]+)?)")


def _hermes_turbo_home() -> Path:
    """Return ``$TOTA_HOME`` falling back to ``$HERMES_HOME`` then ``~/.hermes_turbo``.

    Imports ``hermes_constants.get_hermes_home`` when available so the
    profile-aware resolution stays in one place.  Falls back to a stdlib-
    only lookup when the script runs outside the Hermes Turbo process tree (e.g.
    a fresh checkout, CI, system Python).
    """
    try:
        # Add repo root to sys.path so the import resolves when the skill
        # script runs out-of-process (e.g. `python skills/.../map_project.py`).
        repo_root = Path(__file__).resolve().parents[4]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from hermes_constants import get_hermes_home  # type: ignore[import-not-found]
        return get_hermes_home()
    except (ImportError, ModuleNotFoundError, ValueError):
        for env_var in ("HERMES_TURBO_HOME", "HERMES_TURBO_HOME", "HERMES_HOME"):
            val = os.environ.get(env_var, "").strip()
            if val:
                return Path(val).expanduser()
        return Path.home() / ".hermes_turbo"


def _memory_path() -> Path:
    home = _hermes_turbo_home()
    home.mkdir(parents=True, exist_ok=True)
    return home / MEMORY_FILENAME


def _load_memory() -> dict[str, dict[str, Any]]:
    path = _memory_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_memory(memory: dict[str, dict[str, Any]]) -> None:
    path = _memory_path()
    path.write_text(json.dumps(memory, indent=2, sort_keys=True), encoding="utf-8")


def _git_remote(project_root: Path) -> str | None:
    git_dir = project_root / ".git"
    if not git_dir.exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(project_root), "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() or None


def _is_fresh(entry: dict[str, Any], ttl_days: int) -> bool:
    mapped_at = entry.get("mapped_at")
    if not mapped_at:
        return False
    try:
        ts = _dt.datetime.fromisoformat(mapped_at.replace("Z", "+00:00"))
    except ValueError:
        return False
    now = _dt.datetime.now(_dt.timezone.utc)
    return (now - ts).days < ttl_days


def _agents_md_present(project_root: Path) -> bool:
    return (project_root / "AGENTS.md").exists()


def _ralph_ready(project_root: Path) -> bool:
    """True when the mapper produced enough of its AGENTS.md ecosystem.

    The mapper's stable output set on a successful run is AGENTS.md +
    INIT.md + _BOOTSTRAP.md (plus CLAUDE.md, README mirrors, and the
    `.agents/` / `.claude/` / `.codex/` / `.skills/` directories — those
    vary across mapper versions so we don't assert on them).  Presence
    of all three core docs is the minimum surface a `/goal` (Ralph) loop
    needs to make non-trivial progress without re-onboarding mid-flight.
    """
    return all((project_root / name).exists() for name in _RALPH_MIN_ARTIFACTS)


def _extract_mapper_version(stdout: str) -> str:
    """Parse the mapper's banner for its self-reported version.

    The mapper prints a banner like ``LLM Project Mapper - Bootstrap (npx)\n  v0.2.0``
    on every run; pulling the version from there avoids a second
    ``npx --yes`` invocation (which would re-install or even re-execute
    the mapper on a cache miss).
    """
    if not stdout:
        return "unknown"
    match = _MAPPER_VERSION_RE.search(stdout)
    return match.group(1) if match else "unknown"


def _run_mapper(project_root: Path) -> tuple[bool, str]:
    npx = shutil.which("npx")
    if not npx:
        return False, "npx is not installed; install Node.js >=16.7 to use the mapper."
    try:
        result = subprocess.run(
            [npx, "--yes", MAPPER_NPM_PACKAGE],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "llm-project-mapper timed out after 600s."
    except OSError as exc:
        return False, f"failed to spawn npx: {exc}"
    if result.returncode != 0:
        msg = (result.stderr or result.stdout or "").strip()[:500]
        return False, f"mapper exited with code {result.returncode}: {msg}"
    return True, (result.stdout or "").strip()


def map_project(project_root: Path, force: bool, ttl_days: int) -> dict[str, Any]:
    project_root = project_root.resolve()
    if not project_root.is_dir():
        return {"ok": False, "error": f"project_root not a directory: {project_root}"}

    memory = _load_memory()
    key = str(project_root)
    existing = memory.get(key)

    if existing and not force and _is_fresh(existing, ttl_days) and _agents_md_present(project_root):
        return {"ok": True, "skipped": True, "reason": "already_mapped_recent", "entry": existing}

    ok, output = _run_mapper(project_root)
    if not ok:
        return {"ok": False, "error": output}

    entry = {
        "project_root": str(project_root),
        "git_remote": _git_remote(project_root),
        "mapped_at": _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "mapper_version": _extract_mapper_version(output),
        "agents_md_present": _agents_md_present(project_root),
        "ralph_ready": _ralph_ready(project_root),
    }
    memory[key] = entry
    _save_memory(memory)

    return {"ok": True, "skipped": False, "entry": entry, "mapper_output": output[:500]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Map a code project with llm-project-mapper.")
    parser.add_argument("--project-root", default=os.getcwd(), help="Path to the project root (default: cwd).")
    parser.add_argument("--force", action="store_true", help="Re-map even if a fresh entry exists in memory.")
    parser.add_argument("--ttl-days", type=int, default=DEFAULT_TTL_DAYS, help="Days after which a mapping is considered stale.")
    args = parser.parse_args(argv)

    result = map_project(Path(args.project_root), force=args.force, ttl_days=args.ttl_days)
    json.dump(result, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
