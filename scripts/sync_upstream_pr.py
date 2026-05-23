#!/usr/bin/env python3
"""Create an upstream-sync branch and report whether it's PR-ready.

Used by the ``auto-sync-pr`` GitHub Actions workflow. Runs inside a checkout
and:

  1. creates a dated sync branch off the current default branch,
  2. merges ``<upstream>/<branch>`` (no-edit),
  3. on conflicts: aborts the merge and reports ``conflicts`` (the workflow
     opens a tracking issue instead of a broken PR),
  4. on a clean merge: runs the validation gate (sync-policy validator +
     a focused pytest subset) and reports ``gate_passed``.

It does NOT push or open the PR — that's the workflow's job, where GitHub
auth lives. This keeps the sync logic deterministic and unit-testable: all
git/command access goes through injectable runners.

Exit codes:
  0  clean merge + gate passed  -> workflow pushes branch + opens draft PR
  10 merge conflicts            -> workflow opens/refreshes a tracking issue
  20 gate failed                -> workflow opens/refreshes a tracking issue
  30 nothing to merge           -> workflow does nothing
  1  unexpected error
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable, Optional


UPSTREAM_URL = "https://github.com/NousResearch/hermes-agent.git"
UPSTREAM_BRANCH = "main"

EXIT_READY = 0
EXIT_ERROR = 1
EXIT_CONFLICTS = 10
EXIT_GATE_FAILED = 20
EXIT_NOTHING = 30


GitRunner = Callable[[list], subprocess.CompletedProcess]


@dataclass
class SyncResult:
    ok: bool
    branch: str = ""
    base_branch: str = ""
    upstream: str = ""
    merged: bool = False
    nothing_to_merge: bool = False
    conflicts: list = field(default_factory=list)
    gate_passed: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    def exit_code(self) -> int:
        if not self.ok:
            return EXIT_ERROR
        if self.nothing_to_merge:
            return EXIT_NOTHING
        if self.conflicts:
            return EXIT_CONFLICTS
        if not self.gate_passed:
            return EXIT_GATE_FAILED
        return EXIT_READY


def _default_git_runner(cwd: Path) -> GitRunner:
    def run(args: list) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        )
    return run


def detect_base_branch(git: GitRunner) -> str:
    """Current branch name, or 'HEAD' detached fallback."""
    res = git(["rev-parse", "--abbrev-ref", "HEAD"])
    name = (res.stdout or "").strip()
    return name or "HEAD"


def _conflicted_files(git: GitRunner) -> list:
    res = git(["diff", "--name-only", "--diff-filter=U"])
    return [l for l in (res.stdout or "").splitlines() if l.strip()]


def run_gate(
    cwd: Path,
    *,
    runner: Optional[Callable[[list], subprocess.CompletedProcess]] = None,
    skip_tests: bool = False,
) -> tuple[bool, str]:
    """Validation gate: sync-policy validator + focused pytest subset.

    Returns (passed, detail). Injectable ``runner`` for tests.
    """
    def _run(cmd: list) -> subprocess.CompletedProcess:
        if runner is not None:
            return runner(cmd)
        return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)

    policy = _run([sys.executable, "scripts/validate_sync_policy.py"])
    if policy.returncode != 0:
        return False, f"sync-policy validator failed: {(policy.stdout or policy.stderr)[:400]}"

    if skip_tests:
        return True, "policy ok; tests skipped"

    tests = _run([
        sys.executable, "-m", "pytest", "-o", "addopts=",
        "tests/test_validate_sync_policy.py",
        "tests/test_hermes_constants.py",
        "-q", "--tb=short",
    ])
    if tests.returncode != 0:
        return False, f"pytest gate failed: {(tests.stdout or tests.stderr)[-400:]}"
    return True, "policy + focused tests passed"


def sync(
    cwd: Path,
    *,
    upstream_url: str = UPSTREAM_URL,
    upstream_branch: str = UPSTREAM_BRANCH,
    base_branch: Optional[str] = None,
    git: Optional[GitRunner] = None,
    gate: Optional[Callable[[], tuple[bool, str]]] = None,
    now: Optional[str] = None,
) -> SyncResult:
    """Create the sync branch and merge upstream. Pure-ish: git is injectable."""
    git = git or _default_git_runner(cwd)
    base = base_branch or detect_base_branch(git)
    stamp = now or time.strftime("%Y%m%d-%H%M%S")
    branch = f"sync/upstream-{stamp}"
    res = SyncResult(ok=True, base_branch=base, upstream=f"{upstream_url}#{upstream_branch}")

    # Ensure upstream remote + fetch.
    git(["remote", "add", "upstream", upstream_url])  # ok if it already exists
    fetch = git(["fetch", "upstream", upstream_branch, "--prune"])
    if fetch.returncode != 0:
        res.ok = False
        res.error = f"fetch upstream failed: {(fetch.stderr or '').strip()[:300]}"
        return res

    # Anything to merge?
    behind = git(["rev-list", "--count", f"HEAD..upstream/{upstream_branch}"])
    try:
        count = int((behind.stdout or "0").strip())
    except ValueError:
        count = 0
    if count == 0:
        res.nothing_to_merge = True
        return res

    # Create dated branch off current HEAD.
    cb = git(["checkout", "-B", branch])
    if cb.returncode != 0:
        res.ok = False
        res.error = f"could not create branch {branch}: {(cb.stderr or '').strip()[:200]}"
        return res
    res.branch = branch

    merge = git(["merge", "--no-edit", f"upstream/{upstream_branch}"])
    if merge.returncode != 0:
        res.conflicts = _conflicted_files(git)
        # Leave the merge aborted so the checkout is clean for the next run.
        git(["merge", "--abort"])
        if not res.conflicts:
            res.error = (merge.stderr or "merge failed").strip()[:300]
        return res
    res.merged = True

    passed, detail = gate() if gate else run_gate(cwd)
    res.gate_passed = passed
    if not passed:
        res.error = detail
    return res


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--upstream-url", default=UPSTREAM_URL)
    parser.add_argument("--upstream-branch", default=UPSTREAM_BRANCH)
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--skip-tests", action="store_true",
                        help="run only the sync-policy validator in the gate")
    args = parser.parse_args(argv)

    def _gate():
        return run_gate(args.repo, skip_tests=args.skip_tests)

    result = sync(
        args.repo,
        upstream_url=args.upstream_url,
        upstream_branch=args.upstream_branch,
        base_branch=args.base_branch,
        gate=_gate,
    )
    json.dump(result.to_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return result.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
