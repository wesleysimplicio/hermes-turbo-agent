"""Hermes Turbo Agent self-update prompt.

This module is intentionally small and dependency-free so installed users get
release prompts without pulling extra packages into CLI startup.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any


TOTA_RELEASES_API = "https://api.github.com/repos/wesleysimplicio/hermes-turbo-agent/releases/latest"
TOTA_GIT_URL = "https://github.com/wesleysimplicio/hermes-turbo-agent.git"
PROMPT_CACHE_SECONDS = 24 * 3600
CHECK_CACHE_SECONDS = 6 * 3600


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _disabled() -> bool:
    return _truthy_env("TOTA_SKIP_UPDATE_PROMPT") or (
        (os.environ.get("TOTA_UPDATE_PROMPT") or "").strip().lower() in {"0", "false", "no", "off"}
    )


def _version_tuple(value: str) -> tuple[int, ...]:
    match = re.search(r"(\d+(?:\.\d+){1,3})", value or "")
    if not match:
        return (0,)
    return tuple(int(part) for part in match.group(1).split("."))


def _cache_path() -> Path:
    try:
        from hermes_constants import get_hermes_home

        return get_hermes_home() / ".tota_update_prompt.json"
    except Exception:
        return Path.home() / ".tota_update_prompt.json"


def _read_cache() -> dict[str, Any]:
    path = _cache_path()
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}
    return {}


def _write_cache(data: dict[str, Any]) -> None:
    path = _cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except Exception:
        pass


def _fetch_latest_release() -> dict[str, str] | None:
    now = time.time()
    cache = _read_cache()
    latest = cache.get("latest")
    if (
        isinstance(latest, dict)
        and now - float(latest.get("checked_at", 0) or 0) < CHECK_CACHE_SECONDS
        and latest.get("tag_name")
    ):
        return {
            "tag_name": str(latest["tag_name"]),
            "html_url": str(latest.get("html_url") or ""),
            "name": str(latest.get("name") or latest["tag_name"]),
        }

    try:
        req = urllib.request.Request(
            TOTA_RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "tota-agent-update-check",
            },
        )
        with urllib.request.urlopen(req, timeout=2.5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict) or not payload.get("tag_name"):
        return None
    release = {
        "tag_name": str(payload.get("tag_name")),
        "html_url": str(payload.get("html_url") or ""),
        "name": str(payload.get("name") or payload.get("tag_name")),
    }
    cache["latest"] = {**release, "checked_at": now}
    _write_cache(cache)
    return release


def latest_release_update(current_version: str | None = None) -> dict[str, str] | None:
    """Return latest release metadata when Tota has a newer release."""
    if current_version is None:
        from hermes_cli import __version__

        current_version = __version__
    release = _fetch_latest_release()
    if not release:
        return None
    if _version_tuple(release["tag_name"]) <= _version_tuple(current_version):
        return None
    return release


def _should_prompt(tag: str, now: float | None = None) -> bool:
    now = time.time() if now is None else now
    cache = _read_cache()
    prompt = cache.get("prompt")
    if not isinstance(prompt, dict):
        return True
    if prompt.get("tag_name") != tag:
        return True
    return now - float(prompt.get("last_prompted_at", 0) or 0) >= PROMPT_CACHE_SECONDS


def _record_prompt(tag: str, answer: str) -> None:
    cache = _read_cache()
    cache["prompt"] = {
        "tag_name": tag,
        "answer": answer,
        "last_prompted_at": time.time(),
    }
    _write_cache(cache)


def update_command() -> list[str]:
    """Return the command used when a user accepts the Tota update prompt."""
    project_root = Path(__file__).resolve().parents[1]
    if (project_root / ".git").is_dir():
        return [sys.executable, "-m", "hermes_cli.main", "update", "--yes"]

    uv = shutil.which("uv")
    if uv:
        return [uv, "pip", "install", "--upgrade", f"git+{TOTA_GIT_URL}"]
    return [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{TOTA_GIT_URL}"]


def update_command_label() -> str:
    return " ".join(update_command())


def maybe_prompt_for_tota_update() -> bool:
    """Ask interactive users whether they want to update to a new Hermes Turbo release.

    Returns True only when the prompt ran an update command successfully enough
    for the current process to exit and let the user restart.
    """
    if _disabled() or not sys.stdin.isatty() or not sys.stdout.isatty():
        return False

    release = latest_release_update()
    if not release:
        return False

    tag = release["tag_name"]
    if not _should_prompt(tag):
        return False

    from hermes_cli import __version__

    print()
    print(f"Hermes Turbo Agent {tag} is available. You are running {__version__}.")
    if release.get("html_url"):
        print(f"Release notes: {release['html_url']}")
    print(f"Update command: {update_command_label()}")

    try:
        answer = input("Update Hermes Turbo Agent now? [Y/n] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        answer = "n"

    normalized = answer or "y"
    _record_prompt(tag, normalized)
    if normalized not in {"y", "yes"}:
        print("Skipping update for now. Hermes Turbo Agent will remind you later.")
        return False

    env = os.environ.copy()
    env["TOTA_SKIP_UPDATE_PROMPT"] = "1"
    result = subprocess.run(update_command(), env=env)
    if result.returncode == 0:
        print("Hermes Turbo Agent updated. Restart the command to use the new version.")
        raise SystemExit(0)
    print("Hermes Turbo Agent update failed. Run the update command manually to inspect the error.")
    return False
