#!/usr/bin/env python3
"""Validate the machine-readable Hermes Turbo upstream sync policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_POLICY = ROOT / "docs" / "hermes-turbo-sync-policy.json"
VALID_STRATEGIES = {
    "keep-turbo",
    "prefer-upstream",
    "merge",
    "regenerate",
    "manual-review",
}
GLOB_CHARS = set("*?[")


def _is_glob(pattern: str) -> bool:
    return any(char in pattern for char in GLOB_CHARS)


def _static_prefix(pattern: str) -> Path:
    parts: list[str] = []
    for part in Path(pattern).parts:
        if any(char in part for char in GLOB_CHARS):
            break
        parts.append(part)
    if not parts:
        return Path(".")
    return Path(*parts)


def _validate_path(repo_root: Path, pattern: str, allow_empty: bool) -> list[str]:
    errors: list[str] = []
    if not pattern:
        return ["path entries must be non-empty strings"]
    candidate = repo_root / pattern
    if not _is_glob(pattern):
        if not candidate.exists():
            errors.append(f"missing path: {pattern}")
        return errors
    prefix = repo_root / _static_prefix(pattern)
    probe = prefix
    while probe != repo_root and not probe.exists():
        probe = probe.parent
    if not probe.exists():
        errors.append(f"glob prefix does not exist: {pattern}")
        return errors
    matches = list(repo_root.glob(pattern))
    if not matches and not allow_empty:
        errors.append(f"glob matched nothing: {pattern}")
    return errors


def validate_policy(policy_path: Path, repo_root: Path) -> list[str]:
    data = json.loads(policy_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        return ["policy must define a non-empty `rules` list"]
    for index, rule in enumerate(rules, start=1):
        name = rule.get("name", f"rule-{index}")
        strategy = rule.get("strategy")
        if strategy not in VALID_STRATEGIES:
            errors.append(f"{name}: invalid strategy {strategy!r}")
        paths = rule.get("paths")
        if not isinstance(paths, list) or not paths:
            errors.append(f"{name}: `paths` must be a non-empty list")
            continue
        allow_empty_globs = {
            entry for entry in rule.get("allow_empty_globs", []) if isinstance(entry, str)
        }
        allow_missing_paths = {
            entry for entry in rule.get("allow_missing_paths", []) if isinstance(entry, str)
        }
        for pattern in paths:
            if not isinstance(pattern, str):
                errors.append(f"{name}: path entries must be strings")
                continue
            if pattern in allow_missing_paths and not _is_glob(pattern):
                continue
            errors.extend(
                f"{name}: {message}"
                for message in _validate_path(
                    repo_root,
                    pattern,
                    allow_empty=pattern in allow_empty_globs,
                )
            )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--repo-root", default=str(ROOT))
    args = parser.parse_args()

    policy_path = Path(args.policy).resolve()
    repo_root = Path(args.repo_root).resolve()
    errors = validate_policy(policy_path, repo_root)
    if errors:
        print(json.dumps({"ok": False, "errors": errors}, indent=2))
        return 1
    print(json.dumps({"ok": True, "policy": str(policy_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
