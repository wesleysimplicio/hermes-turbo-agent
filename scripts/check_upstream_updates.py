#!/usr/bin/env python3
"""Detect whether upstream Hermes has advanced beyond our last integrated SHA.

Used by the scheduled ``auto-update-check`` GitHub Actions workflow to decide
whether to alert maintainers (open/refresh a tracking issue) that there are new
upstream commits to sync. Pure stdlib so it runs anywhere without installs.

It compares two things:

  - ``last_sync_sha`` recorded in ``scripts/upstream-sync/sync-state.json``
  - the current HEAD of the upstream default branch (via ``git ls-remote``)

Exit codes:
  0  up to date (no drift)            -> workflow does nothing
  10 drift detected (new commits)     -> workflow opens/updates the alert
  1  error (network, parse, etc.)     -> workflow surfaces the failure

Prints a JSON object to stdout in all cases so the workflow can read details.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parent.parent
SYNC_STATE = ROOT / "scripts" / "upstream-sync" / "sync-state.json"

EXIT_UP_TO_DATE = 0
EXIT_ERROR = 1
EXIT_DRIFT = 10


def load_sync_state(path: Path = SYNC_STATE) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def ls_remote_head(url: str, branch: str) -> Optional[str]:
    """Return the SHA at ``refs/heads/<branch>`` of the remote, or None."""
    proc = subprocess.run(
        ["git", "ls-remote", url, f"refs/heads/{branch}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        return None
    line = proc.stdout.strip().splitlines()
    if not line:
        return None
    sha = line[0].split("\t", 1)[0].strip()
    return sha or None


def check(state: dict, *, head_resolver=None) -> dict:
    """Compute the drift verdict. ``head_resolver`` is injectable for tests.

    Resolved at call time so monkeypatching the module-level
    :func:`ls_remote_head` is honoured by :func:`main`.
    """
    resolver = head_resolver or ls_remote_head
    url = state.get("upstream_url") or "https://github.com/NousResearch/hermes-agent.git"
    branch = state.get("upstream_branch") or "main"
    last = (state.get("last_sync_sha") or "").strip()

    remote_head = resolver(url, branch)
    if remote_head is None:
        return {
            "ok": False,
            "error": f"could not read upstream HEAD for {url}#{branch}",
            "upstream_url": url,
            "upstream_branch": branch,
        }

    if not last:
        # No baseline recorded yet — treat as drift so the first sync is flagged.
        return {
            "ok": True,
            "drift": True,
            "reason": "no last_sync_sha recorded; first sync needed",
            "upstream_url": url,
            "upstream_branch": branch,
            "remote_head": remote_head,
            "last_sync_sha": "",
        }

    drift = (remote_head != last)
    return {
        "ok": True,
        "drift": drift,
        "reason": "upstream advanced" if drift else "in sync",
        "upstream_url": url,
        "upstream_branch": branch,
        "remote_head": remote_head,
        "last_sync_sha": last,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=SYNC_STATE,
                        help="path to sync-state.json")
    args = parser.parse_args(argv)

    state = load_sync_state(args.state)
    verdict = check(state)
    json.dump(verdict, sys.stdout, indent=2)
    sys.stdout.write("\n")

    if not verdict.get("ok"):
        return EXIT_ERROR
    return EXIT_DRIFT if verdict.get("drift") else EXIT_UP_TO_DATE


if __name__ == "__main__":
    raise SystemExit(main())
