#!/usr/bin/env python3
"""Daily Tota Agent sync routine.

The routine keeps Tota Agent close to NousResearch/hermes-agent while preserving
Tota-specific speed and branding work. It runs in an isolated checkout, creates
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
ORIGIN_URL = "https://github.com/wesleysimplicio/tota-agent.git"
UPSTREAM_URL = "https://github.com/NousResearch/hermes-agent.git"
DEFAULT_PYTHON = "3.14.5"
STATE_DIR = Path.home() / ".local" / "state" / "tota-agent" / "hermes-sync"


class StepError(RuntimeError):
    """Raised when a command step fails."""


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
        "# Tota Agent Daily Hermes Sync",
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
    _run(["git", "clone", ORIGIN_URL, str(checkout)], cwd=repo)
    _ensure_remote(checkout, "upstream", UPSTREAM_URL)
    _git(checkout, "fetch", "origin", "main", "--prune")
    _git(checkout, "fetch", "upstream", "main", "--prune")
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


def _merge_upstream(worktree: Path) -> None:
    result = _git(worktree, "merge", "--no-edit", "upstream/main", check=False)
    if result.returncode == 0:
        return
    conflicts = _git(worktree, "diff", "--name-only", "--diff-filter=U", check=False).stdout.strip()
    raise StepError(
        "upstream merge needs manual conflict resolution"
        + (f"\nConflicted files:\n{conflicts}" if conflicts else "")
    )


def _create_sync_branch(worktree: Path, branch: str) -> None:
    _git(worktree, "checkout", "-B", branch)


def _run_validation(worktree: Path, skip_tests: bool) -> None:
    python_bin = worktree / ".venv" / "bin" / "python"
    _run(
        [
            str(python_bin),
            "-m",
            "py_compile",
            "scripts/tota_hermes_daily_update.py",
            "scripts/benchmark_tota_vs_hermes_0140.py",
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


def _assert_tota_personality(worktree: Path) -> None:
    checks = {
        "README.md": "Tota Agent",
        "pyproject.toml": "msgspec",
        "hermes_constants.py": "TOTA_HOME",
        "agent/_fastjson.py": "orjson",
    }
    missing = []
    for rel_path, needle in checks.items():
        path = worktree / rel_path
        if not path.exists() or needle not in path.read_text(encoding="utf-8", errors="ignore"):
            missing.append(f"{rel_path}: missing {needle!r}")
    if missing:
        raise StepError("Tota personalization checks failed:\n" + "\n".join(missing))


def _commit_and_push(worktree: Path, branch: str, dry_run: bool) -> str:
    status = _git(worktree, "status", "--porcelain").stdout.strip()
    if not status:
        return "no changes"
    if dry_run:
        return "changes left uncommitted because --dry-run was used"
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", f"chore: sync Tota Agent with Hermes upstream {time.strftime('%Y-%m-%d')}")
    _git(worktree, "push", "-u", "origin", branch)
    return "committed and pushed"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=str(REPO_ROOT), help="Tota Agent repository path")
    parser.add_argument("--state-dir", default=str(STATE_DIR), help="State/report directory")
    parser.add_argument("--python-version", default=DEFAULT_PYTHON)
    parser.add_argument("--skip-tool-upgrade", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    state_dir = Path(args.state_dir).expanduser().resolve()
    branch = f"codex/tota-hermes-daily-{time.strftime('%Y%m%d-%H%M%S')}"
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
        _merge_upstream(worktree)
        report["steps"].append("merged upstream/main from NousResearch/hermes-agent")
        _assert_tota_personality(worktree)
        report["steps"].append("verified Tota identity and speed customizations are still present")
        _run_validation(worktree, skip_tests=args.skip_tests)
        report["steps"].append("ran focused validation and taskflow")
        pr_body_path = _run_benchmark_refresh(worktree, state_dir)
        report["steps"].append("validated sync policy and refreshed benchmark artifacts with stale marker support")
        report["pr_body_path"] = str(pr_body_path)
        commit_status = _commit_and_push(worktree, branch, dry_run=args.dry_run)
        report["steps"].append(commit_status)
        report["status"] = "passed"
        return_code = 0
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = str(exc)
        return_code = 1
    finally:
        report["finished_at"] = _now()
        _write_report(report, state_dir)
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
