#!/usr/bin/env python3
"""Daily Hermes Turbo Agent sync routine.

The routine keeps Hermes Turbo Agent close to NousResearch/hermes-agent while preserving
Hermes Turbo-specific speed and branding work. It runs in an isolated checkout, creates
a dated branch, runs the project's own update path, merges upstream Hermes, then
validates before committing and pushing the sync branch.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ORIGIN_URL = "https://github.com/wesleysimplicio/hermes-turbo-agent.git"
UPSTREAM_URL = "https://github.com/NousResearch/hermes-agent.git"
DEFAULT_PYTHON = "3.14.5"
STATE_DIR = Path.home() / ".local" / "state" / "hermes-turbo-agent" / "hermes-sync"


class StepError(RuntimeError):
    """Raised when a command step fails."""


class ConflictError(StepError):
    """Upstream merge produced conflicts that need human resolution."""

    def __init__(self, conflicts: list[str], wip_branch: str) -> None:
        super().__init__(
            f"upstream merge needs manual conflict resolution on branch {wip_branch!r}"
            + (f"\nConflicted files:\n" + "\n".join(conflicts) if conflicts else "")
        )
        self.conflicts = conflicts
        self.wip_branch = wip_branch


# Transient git failure markers we should retry on. Anything else aborts immediately.
_TRANSIENT_NETWORK_MARKERS = (
    "could not resolve host",
    "connection timed out",
    "connection reset",
    "operation timed out",
    "early eof",
    "the remote end hung up",
    "rpc failed",
    "ssl_read",
    "tls",
    "503",
    "504",
)


def _looks_transient(stderr: str) -> bool:
    blob = (stderr or "").lower()
    return any(marker in blob for marker in _TRANSIENT_NETWORK_MARKERS)


def _retry_network(
    cmd: list[str],
    *,
    cwd: Path,
    attempts: int = 4,
    backoff: tuple[int, ...] = (2, 4, 8, 16),
) -> subprocess.CompletedProcess[str]:
    """Run *cmd* with retries for transient network failures.

    Permanent errors (auth, ref not found, etc.) abort on the first try.
    """
    last_result: subprocess.CompletedProcess[str] | None = None
    for attempt in range(1, attempts + 1):
        result = _run(cmd, cwd=cwd, check=False)
        last_result = result
        if result.returncode == 0:
            return result
        if not _looks_transient(result.stderr):
            raise StepError(
                f"command failed ({result.returncode}, permanent): {' '.join(cmd)}"
            )
        if attempt == attempts:
            break
        wait = backoff[min(attempt - 1, len(backoff) - 1)]
        print(
            f"[retry] {' '.join(cmd)} failed transiently; sleeping {wait}s "
            f"before attempt {attempt + 1}/{attempts}",
            file=sys.stderr,
        )
        time.sleep(wait)
    assert last_result is not None
    raise StepError(
        f"command failed after {attempts} transient retries: {' '.join(cmd)}"
    )


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _find_executable(*names: str) -> str | None:
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    for path in (
        "/opt/homebrew/bin/uv",
        "/usr/local/bin/uv",
        str(Path.home() / ".local" / "bin" / "uv"),
        str(Path.home() / ".cargo" / "bin" / "uv"),
    ):
        if Path(path).exists():
            return path
    return None


def _run(
    cmd: list[str],
    *,
    cwd: Path,
    check: bool = True,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    print(f"$ {' '.join(cmd)}")
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        text=True,
        capture_output=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise StepError(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def _git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd, check=check)


def _write_report(report: dict[str, Any], state_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    latest_json = state_dir / "latest.json"
    latest_md = state_dir / "latest.md"
    latest_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# Hermes Turbo Agent Daily Hermes Sync",
        "",
        f"- Status: `{report['status']}`",
        f"- Started: `{report['started_at']}`",
        f"- Finished: `{report.get('finished_at', '')}`",
        f"- Branch: `{report.get('branch', '')}`",
        f"- Worktree: `{report.get('worktree', '')}`",
        "",
        "## Steps",
        "",
    ]
    for step in report.get("steps", []):
        lines.append(f"- {step}")
    if report.get("pr_body_path"):
        lines.extend(["", "## PR Body", "", f"- `{report['pr_body_path']}`"])
    if report.get("error"):
        lines.extend(["", "## Error", "", f"```text\n{report['error']}\n```"])
    latest_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ensure_remote(repo: Path, name: str, url: str) -> None:
    existing = _git(repo, "remote", "get-url", name, check=False)
    if existing.returncode != 0:
        _git(repo, "remote", "add", name, url)
        return
    if existing.stdout.strip() != url:
        _git(repo, "remote", "set-url", name, url)


def _remove_old_checkout(checkout: Path) -> None:
    if not checkout.exists():
        return
    shutil.rmtree(checkout, ignore_errors=True)


def _prepare_checkout(repo: Path, checkout: Path) -> None:
    _ensure_remote(repo, "origin", ORIGIN_URL)
    _ensure_remote(repo, "upstream", UPSTREAM_URL)
    _remove_old_checkout(checkout)
    checkout.parent.mkdir(parents=True, exist_ok=True)
    _retry_network(["git", "clone", ORIGIN_URL, str(checkout)], cwd=repo)
    _ensure_remote(checkout, "upstream", UPSTREAM_URL)
    _retry_network(["git", "fetch", "origin", "main", "--prune"], cwd=checkout)
    _retry_network(["git", "fetch", "upstream", "main", "--prune"], cwd=checkout)
    _git(checkout, "checkout", "-B", "main", "origin/main")
    _git(checkout, "config", "rerere.enabled", "true")


def _upgrade_machine_tools(skip: bool) -> None:
    if skip:
        return
    brew = shutil.which("brew") or "/opt/homebrew/bin/brew"
    if Path(brew).exists():
        _run([brew, "update"], cwd=REPO_ROOT)
        _run([brew, "upgrade", "uv", "python@3.14"], cwd=REPO_ROOT, check=False)


def _prepare_python(worktree: Path, python_version: str, skip_tool_upgrade: bool) -> str:
    _upgrade_machine_tools(skip_tool_upgrade)
    uv = _find_executable("uv")
    if not uv:
        raise StepError("uv is not installed or not on PATH")
    _run([uv, "python", "install", python_version], cwd=worktree)
    _run([uv, "venv", ".venv", "--python", python_version], cwd=worktree)
    _run([uv, "pip", "install", "--python", ".venv/bin/python", "-e", ".[all,dev,fast]"], cwd=worktree)
    return uv


def _run_hermes_update(worktree: Path) -> None:
    hermes_python = worktree / ".venv" / "bin" / "python"
    _run(
        [str(hermes_python), "-m", "hermes_cli.main", "update", "--yes", "--no-backup"],
        cwd=worktree,
    )


def _merge_upstream(worktree: Path, base_branch: str, state_dir: Path) -> None:
    """Merge upstream/main into the worktree.

    On conflict, snapshot the partial state to a dedicated WIP branch so a human
    can resolve from a known commit instead of from a half-merged working tree.
    Raises :class:`ConflictError` (exit code 2 via main) with the conflict list.
    """
    result = _git(worktree, "merge", "--no-edit", "upstream/main", check=False)
    if result.returncode == 0:
        return
    conflicts_raw = _git(
        worktree, "diff", "--name-only", "--diff-filter=U", check=False
    ).stdout.strip()
    conflicts = [line for line in conflicts_raw.splitlines() if line]
    wip_branch = f"{base_branch}-CONFLICT"
    # Stage everything (including conflict markers) and commit so the WIP state is
    # not lost. The commit lives only on the WIP branch, never on `main`.
    _git(worktree, "add", "-A", check=False)
    _git(
        worktree,
        "commit",
        "-m",
        f"WIP: upstream merge conflict during {time.strftime('%Y-%m-%d')} sync",
        "--allow-empty",
        "--no-verify",
        check=False,
    )
    _git(worktree, "checkout", "-B", wip_branch, check=False)
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "latest-conflicts.md").write_text(
        "# Upstream Sync Conflicts\n\n"
        f"- Branch: `{wip_branch}`\n"
        f"- Worktree: `{worktree}`\n\n"
        "## Conflicted files\n\n"
        + ("\n".join(f"- `{f}`" for f in conflicts) if conflicts else "(none reported)\n")
        + "\n",
        encoding="utf-8",
    )
    raise ConflictError(conflicts, wip_branch)


def _create_sync_branch(worktree: Path, branch: str) -> None:
    _git(worktree, "checkout", "-B", branch)


def _run_validation(worktree: Path, skip_tests: bool) -> None:
    python_bin = worktree / ".venv" / "bin" / "python"
    _run(
        [
            str(python_bin),
            "-m",
            "py_compile",
            "scripts/hermes_turbo_daily_update.py",
            "scripts/benchmark_hermes_turbo_vs_hermes_0140.py",
            "run_agent.py",
            "agent/transports/types.py",
        ],
        cwd=worktree,
    )
    if not skip_tests:
        _run(
            [
                str(python_bin),
                "-m",
                "pytest",
                "-o",
                "addopts=",
                "tests/agent/transports/test_types.py",
                "tests/run_agent/test_repair_tool_call_arguments.py",
                "-q",
                "--tb=short",
            ],
            cwd=worktree,
        )
    taskflow = Path.home() / ".local" / "bin" / "taskflow"
    if taskflow.exists():
        _run([str(taskflow), "run", str(worktree)], cwd=worktree)


def _run_benchmark_refresh(worktree: Path, state_dir: Path) -> Path:
    python_bin = worktree / ".venv" / "bin" / "python"
    _run([str(python_bin), "scripts/validate_sync_policy.py"], cwd=worktree)
    _run([str(python_bin), "scripts/check_sync_policy_mirror.py"], cwd=worktree)
    _run([str(python_bin), "scripts/refresh_sync_benchmarks.py", "--python", str(python_bin)], cwd=worktree)
    status_path = worktree / "docs" / "benchmark-refresh-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    pr_body = state_dir / "latest_pr_body.md"
    lines = [
        "# Upstream Sync PR Body",
        "",
        f"- Generated: `{_now()}`",
        f"- Worktree: `{worktree}`",
        "",
        "## Benchmark refresh",
        "",
        f"- Status: `{status['status']}`",
        f"- Stale claims: `{status['stale']}`",
        "",
        "### Deltas",
        "",
    ]
    lines.extend(status.get("delta_lines", []))
    if status.get("error"):
        lines.extend(["", "### Error", "", "```text", status["error"], "```"])
    pr_body.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pr_body


def _assert_hermes_turbo_personality(worktree: Path) -> None:
    checks = {
        "README.md": "Hermes Turbo Agent",
        "pyproject.toml": "msgspec",
        "hermes_constants.py": "HERMES_TURBO_HOME",
        "agent/_fastjson.py": "orjson",
    }
    missing = []
    for rel_path, needle in checks.items():
        path = worktree / rel_path
        if not path.exists() or needle not in path.read_text(encoding="utf-8", errors="ignore"):
            missing.append(f"{rel_path}: missing {needle!r}")
    if missing:
        raise StepError("Hermes Turbo personalization checks failed:\n" + "\n".join(missing))


def _commit_and_push(worktree: Path, branch: str, dry_run: bool) -> str:
    status = _git(worktree, "status", "--porcelain").stdout.strip()
    if not status:
        return "no changes"
    if dry_run:
        return "changes left uncommitted because --dry-run was used"
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", f"chore: sync Hermes Turbo Agent with Hermes upstream {time.strftime('%Y-%m-%d')}")
    _git(worktree, "push", "-u", "origin", branch)
    return "committed and pushed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Hermes Turbo Agent repository path")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="State/report directory")
    parser.add_argument("--python-version", default=DEFAULT_PYTHON)
    parser.add_argument("--skip-tool-upgrade", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser().resolve()
    branch = f"codex/hermes-turbo-hermes-daily-{time.strftime('%Y%m%d-%H%M%S')}"
    worktree = state_dir / "checkout"
    report: dict[str, Any] = {
        "status": "running",
        "started_at": _now(),
        "branch": branch,
        "repo": str(repo),
        "worktree": str(worktree),
        "steps": [],
    }

    try:
        _prepare_checkout(repo, worktree)
        report["steps"].append("prepared isolated sync checkout from origin/main")
        _prepare_python(worktree, args.python_version, args.skip_tool_upgrade)
        report["steps"].append(f"prepared .venv with Python {args.python_version}")
        _run_hermes_update(worktree)
        report["steps"].append("ran hermes update --yes --no-backup inside the sync worktree")
        _create_sync_branch(worktree, branch)
        report["steps"].append("created dated sync branch after hermes update")
        _merge_upstream(worktree, branch, state_dir)
        report["steps"].append("merged upstream/main from NousResearch/hermes-agent")
        _assert_hermes_turbo_personality(worktree)
        report["steps"].append("verified Hermes Turbo identity and speed customizations are still present")
        _run_validation(worktree, skip_tests=args.skip_tests)
        report["steps"].append("ran focused validation and taskflow")
        pr_body_path = _run_benchmark_refresh(worktree, state_dir)
        report["steps"].append("validated sync policy and refreshed benchmark artifacts with stale marker support")
        report["pr_body_path"] = str(pr_body_path)
        commit_status = _commit_and_push(worktree, branch, dry_run=args.dry_run)
        report["steps"].append(commit_status)
        report["status"] = "passed"
        return_code = 0
    except ConflictError as exc:
        report["status"] = "conflict"
        report["error"] = str(exc)
        report["conflicts"] = exc.conflicts
        report["conflict_branch"] = exc.wip_branch
        return_code = 2
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        return_code = 1
    finally:
        report["finished_at"] = _now()
        _write_report(report, state_dir)
        # Cleanup: on hard failure, remove the worktree so the next run starts fresh.
        # Conflict state is preserved (the WIP branch lives in origin if pushed; the
        # worktree itself can be discarded because the branch SHA is in the report).
        if report["status"] == "failed":
            try:
                shutil.rmtree(worktree, ignore_errors=False)
            except OSError as cleanup_exc:
                print(
                    f"[warn] failed to remove worktree {worktree}: {cleanup_exc}",
                    file=sys.stderr,
                )
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
