"""Detect and optionally apply updates from this fork's own default branch.

This backs ``hermes update --check-main``. The existing ``hermes update
--check`` flow compares against *upstream* Hermes (NousResearch). This module
is the complement: it compares the locally checked-out commit against the
fork's own remote default branch (``origin``) so a local deployment can tell
whether new commits landed on main and, optionally, fast-forward to them.

Design notes:

- All git access goes through :func:`_run_git` so tests can stub it.
- ``check_main`` never force-anything: applying an update is a strict
  ``merge --ff-only``. If the local checkout has diverged (ahead, or a
  non-fast-forward), it refuses and asks the caller to resolve manually.
- Network/permission failures degrade gracefully into a result with
  ``error`` set; the caller decides whether that's fatal.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class MainUpdateStatus:
    ok: bool                       # the check itself completed
    branch: str = ""               # default branch compared against
    local_sha: str = ""            # short local HEAD
    remote_sha: str = ""           # short remote HEAD
    behind: int = 0                # commits on remote not in local
    ahead: int = 0                 # local commits not on remote
    applied: bool = False          # an ff-only update was applied
    error: str = ""                # populated on failure

    @property
    def up_to_date(self) -> bool:
        return self.ok and self.behind == 0

    @property
    def can_fast_forward(self) -> bool:
        return self.ok and self.behind > 0 and self.ahead == 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["up_to_date"] = self.up_to_date
        d["can_fast_forward"] = self.can_fast_forward
        return d


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command, capturing output. Never raises on non-zero."""
    cmd = ["git"]
    # On Windows, the atomic-append fetch can break on some filesystems.
    import sys
    if sys.platform == "win32":
        cmd = ["git", "-c", "windows.appendAtomically=false"]
    return subprocess.run(
        cmd + args, cwd=str(cwd), capture_output=True, text=True,
    )


def detect_default_branch(cwd: Path, remote: str = "origin") -> Optional[str]:
    """Best-effort detection of the remote's default branch name.

    Tries ``refs/remotes/<remote>/HEAD`` first, then ``git remote show``.
    Returns ``None`` if it cannot be determined.
    """
    ref = _run_git(["symbolic-ref", f"refs/remotes/{remote}/HEAD"], cwd)
    if ref.returncode == 0 and ref.stdout.strip():
        # e.g. refs/remotes/origin/codex/hermes-agent-100x-fast
        name = ref.stdout.strip().split(f"refs/remotes/{remote}/", 1)[-1]
        if name:
            return name
    show = _run_git(["remote", "show", remote], cwd)
    if show.returncode == 0:
        for line in show.stdout.splitlines():
            line = line.strip()
            if line.startswith("HEAD branch:"):
                return line.split(":", 1)[1].strip()
    return None


def _short(sha: str) -> str:
    return sha.strip()[:12]


def check_main(
    cwd: Path,
    *,
    branch: Optional[str] = None,
    remote: str = "origin",
    apply: bool = False,
) -> MainUpdateStatus:
    """Compare local HEAD against ``<remote>/<branch>`` and optionally ff-update.

    ``branch`` defaults to the remote's detected default branch.
    With ``apply=True`` and a clean fast-forward available, performs
    ``git merge --ff-only`` to advance the working tree.
    """
    if not (cwd / ".git").exists():
        return MainUpdateStatus(ok=False, error="not a git repository")

    if branch is None:
        branch = detect_default_branch(cwd, remote=remote)
        if not branch:
            return MainUpdateStatus(
                ok=False, error="could not detect default branch",
            )

    fetch = _run_git(["fetch", remote, branch], cwd)
    if fetch.returncode != 0:
        stderr = (fetch.stderr or "").strip()
        if "Could not resolve host" in stderr or "unable to access" in stderr:
            msg = "network error reaching remote"
        elif "Authentication failed" in stderr or "could not read Username" in stderr:
            msg = "authentication failed"
        else:
            msg = stderr.splitlines()[0] if stderr else "git fetch failed"
        return MainUpdateStatus(ok=False, branch=branch, error=msg)

    local = _run_git(["rev-parse", "HEAD"], cwd)
    remote_rev = _run_git(["rev-parse", "FETCH_HEAD"], cwd)
    if local.returncode != 0 or remote_rev.returncode != 0:
        return MainUpdateStatus(ok=False, branch=branch, error="could not resolve revisions")
    local_sha = local.stdout.strip()
    remote_sha = remote_rev.stdout.strip()

    behind_res = _run_git(["rev-list", "--count", "HEAD..FETCH_HEAD"], cwd)
    ahead_res = _run_git(["rev-list", "--count", "FETCH_HEAD..HEAD"], cwd)
    try:
        behind = int(behind_res.stdout.strip())
        ahead = int(ahead_res.stdout.strip())
    except ValueError:
        return MainUpdateStatus(
            ok=False, branch=branch, local_sha=_short(local_sha),
            remote_sha=_short(remote_sha), error="could not compute divergence",
        )

    status = MainUpdateStatus(
        ok=True, branch=branch,
        local_sha=_short(local_sha), remote_sha=_short(remote_sha),
        behind=behind, ahead=ahead,
    )

    if apply and status.can_fast_forward:
        ff = _run_git(["merge", "--ff-only", "FETCH_HEAD"], cwd)
        if ff.returncode == 0:
            status.applied = True
        else:
            status.error = (ff.stderr or "fast-forward failed").strip().splitlines()[0]
    return status


def format_status(status: MainUpdateStatus) -> str:
    if not status.ok:
        return f"✗ Could not check main: {status.error}"
    if status.up_to_date:
        return f"✓ Already up to date with origin/{status.branch} ({status.local_sha})."
    lines = []
    word = "commit" if status.behind == 1 else "commits"
    lines.append(
        f"⚕ {status.behind} {word} behind origin/{status.branch} "
        f"(local {status.local_sha} → remote {status.remote_sha})."
    )
    if status.ahead:
        lines.append(
            f"  Note: local is also {status.ahead} commit(s) ahead — "
            f"a fast-forward is not possible; resolve manually."
        )
    if status.applied:
        lines.append("  ✓ Fast-forwarded local checkout to the remote tip.")
    elif status.can_fast_forward:
        lines.append("  Run 'hermes update --check-main --apply' to fast-forward.")
    return "\n".join(lines)


def run_check_main(cwd: Path, *, apply: bool = False, branch: Optional[str] = None) -> int:
    """CLI entry: print status, return process exit code.

    0 = up to date or update applied; 1 = check failed;
    2 = update available but not applied.
    """
    status = check_main(cwd, branch=branch, apply=apply)
    print(format_status(status))
    if not status.ok:
        return 1
    if status.up_to_date or status.applied:
        return 0
    return 2
