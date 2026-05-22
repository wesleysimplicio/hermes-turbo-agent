#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SyncRule:
    pattern: str
    mode: str
    reason: str


@dataclass(frozen=True)
class SyncPolicy:
    upstream_remote: str
    sync_branch_prefix: str
    default_mode: str
    rules: tuple[SyncRule, ...]
    required_commands: tuple[str, ...]
    benchmark_commands: tuple[str, ...]


def load_policy(path: Path) -> SyncPolicy:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules = tuple(
        SyncRule(
            pattern=str(rule["pattern"]),
            mode=str(rule["mode"]),
            reason=str(rule["reason"]),
        )
        for rule in data.get("rules", [])
    )
    validation = data.get("validation") or {}
    return SyncPolicy(
        upstream_remote=str(data["upstream_remote"]),
        sync_branch_prefix=str(data["sync_branch_prefix"]),
        default_mode=str(data.get("default_mode", "merge")),
        rules=rules,
        required_commands=tuple(validation.get("required_commands") or ()),
        benchmark_commands=tuple(validation.get("benchmark_refresh") or ()),
    )


def classify_path(path: str, policy: SyncPolicy) -> SyncRule:
    matches = [
        rule
        for rule in policy.rules
        if fnmatch.fnmatch(path, rule.pattern)
    ]
    if not matches:
        return SyncRule(pattern="*", mode=policy.default_mode, reason="default policy")
    return max(matches, key=lambda rule: len(rule.pattern.replace("*", "")))


def run_git(args: list[str], *, cwd: Path) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def build_branch_name(policy: SyncPolicy, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    return f"{policy.sync_branch_prefix}-{now:%Y%m%d}"


def collect_upstream_commits(repo: Path, upstream_ref: str, base_ref: str) -> list[str]:
    output = run_git(["log", "--oneline", f"{base_ref}..{upstream_ref}"], cwd=repo)
    return output.splitlines() if output else []


def collect_changed_paths(repo: Path, upstream_ref: str, base_ref: str) -> list[str]:
    output = run_git(["diff", "--name-only", f"{base_ref}..{upstream_ref}"], cwd=repo)
    return sorted(output.splitlines()) if output else []


def render_sync_report(
    *,
    policy: SyncPolicy,
    upstream_ref: str,
    branch_name: str,
    upstream_commits: list[str],
    changed_paths: list[str],
    conflicts: list[str],
) -> str:
    classified = [(path, classify_path(path, policy)) for path in changed_paths]
    lines = [
        "# Hermes Turbo upstream sync report",
        "",
        f"- upstream_ref: `{upstream_ref}`",
        f"- branch: `{branch_name}`",
        f"- upstream_commits: {len(upstream_commits)}",
        f"- changed_paths: {len(changed_paths)}",
        f"- conflicts: {len(conflicts)}",
        "",
        "## Upstream Commits",
    ]
    lines.extend(f"- `{commit}`" for commit in upstream_commits[:80])
    if len(upstream_commits) > 80:
        lines.append(f"- ... omitted {len(upstream_commits) - 80} more commits")

    lines.extend(["", "## Path Policy"])
    for path, rule in classified[:160]:
        lines.append(f"- `{path}` -> `{rule.mode}` via `{rule.pattern}`")
    if len(classified) > 160:
        lines.append(f"- ... omitted {len(classified) - 160} more paths")

    lines.extend(["", "## Conflicts"])
    if conflicts:
        lines.extend(f"- `{path}`" for path in conflicts)
    else:
        lines.append("- none detected yet")

    lines.extend(["", "## Required Validation"])
    lines.extend(f"- `{command}`" for command in policy.required_commands)

    lines.extend(["", "## Benchmark Refresh"])
    lines.extend(f"- `{command}`" for command in policy.benchmark_commands)

    lines.extend(
        [
            "",
            "## Reapply Rules",
            "- Keep Hermes Turbo branding, token saver, desktop/car profiles, and home compatibility unless a policy rule says otherwise.",
            "- Prefer upstream provider/runtime changes unless they conflict with a documented Turbo patch.",
            "- Regenerate benchmark claims from measured data after every successful sync.",
        ]
    )
    return "\n".join(lines) + "\n"


def _ensure_remote(repo: Path, policy: SyncPolicy, remote_name: str) -> None:
    remotes = run_git(["remote"], cwd=repo).splitlines()
    if remote_name in remotes:
        current_url = run_git(["remote", "get-url", remote_name], cwd=repo)
        if current_url != policy.upstream_remote:
            run_git(["remote", "set-url", remote_name, policy.upstream_remote], cwd=repo)
        return
    run_git(["remote", "add", remote_name, policy.upstream_remote], cwd=repo)


def _fetch_upstream_ref(repo: Path, *, remote_name: str, upstream_ref: str) -> None:
    prefix = f"{remote_name}/"
    if upstream_ref.startswith(prefix):
        branch = upstream_ref.removeprefix(prefix)
        run_git(["fetch", "--quiet", remote_name, branch], cwd=repo)
        return
    run_git(["fetch", "--quiet", remote_name], cwd=repo)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan or start a Hermes upstream sync while preserving Turbo patches."
    )
    parser.add_argument("--repo", default=".", help="Repository root")
    parser.add_argument(
        "--policy",
        default="docs/hermes-upstream-sync-policy.yaml",
        help="Sync policy YAML path",
    )
    parser.add_argument("--upstream-remote-name", default="hermes-upstream")
    parser.add_argument("--upstream-ref", default="hermes-upstream/main")
    parser.add_argument("--base-ref", default="HEAD")
    parser.add_argument("--report", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    policy_path = (repo / args.policy).resolve()
    policy = load_policy(policy_path)
    branch_name = build_branch_name(policy)

    _ensure_remote(repo, policy, args.upstream_remote_name)
    _fetch_upstream_ref(
        repo,
        remote_name=args.upstream_remote_name,
        upstream_ref=args.upstream_ref,
    )

    upstream_commits = collect_upstream_commits(repo, args.upstream_ref, args.base_ref)
    changed_paths = collect_changed_paths(repo, args.upstream_ref, args.base_ref)
    report = render_sync_report(
        policy=policy,
        upstream_ref=args.upstream_ref,
        branch_name=branch_name,
        upstream_commits=upstream_commits,
        changed_paths=changed_paths,
        conflicts=[],
    )

    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
    else:
        print(report)

    if args.dry_run:
        return 0

    current_branch = run_git(["branch", "--show-current"], cwd=repo)
    run_git(["switch", "-c", branch_name], cwd=repo)
    try:
        run_git(["merge", "--no-edit", args.upstream_ref], cwd=repo)
    except subprocess.CalledProcessError:
        conflicts = run_git(["diff", "--name-only", "--diff-filter=U"], cwd=repo)
        conflict_list = conflicts.splitlines() if conflicts else []
        conflict_report = render_sync_report(
            policy=policy,
            upstream_ref=args.upstream_ref,
            branch_name=branch_name,
            upstream_commits=upstream_commits,
            changed_paths=changed_paths,
            conflicts=conflict_list,
        )
        report_path = repo / "docs" / "hermes-upstream-sync-last-report.md"
        report_path.write_text(conflict_report, encoding="utf-8")
        print(conflict_report)
        return 2

    print(f"created sync branch {branch_name} from {current_branch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
