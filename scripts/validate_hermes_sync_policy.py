#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml


VALID_MODES = {"keep-turbo", "prefer-upstream", "merge", "regenerate", "manual-review"}
REQUIRED_PATTERNS = {
    "README.md",
    "hermes-turbo-agent.html",
    "distributions/hermes-turbo-*",
    "hermes_constants.py",
    "plugins/token_saver/**",
    "docs/hermes-upstream-sync-policy.yaml",
    "docs/assets/hermes-turbo-brand/**",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def validate_policy_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing policy file: {path}"]

    data = _load_yaml(path)
    if data.get("version") != 1:
        errors.append("version must be 1")
    if not data.get("upstream_remote"):
        errors.append("upstream_remote is required")
    if not data.get("sync_branch_prefix"):
        errors.append("sync_branch_prefix is required")

    rules = data.get("rules")
    if not isinstance(rules, list) or not rules:
        errors.append("rules must be a non-empty list")
        return errors

    seen_patterns: set[str] = set()
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            errors.append(f"rules[{index}] must be an object")
            continue
        pattern = rule.get("pattern")
        mode = rule.get("mode")
        reason = rule.get("reason")
        if not isinstance(pattern, str) or not pattern.strip():
            errors.append(f"rules[{index}].pattern is required")
        else:
            seen_patterns.add(pattern)
        if mode not in VALID_MODES:
            errors.append(f"rules[{index}].mode must be one of {sorted(VALID_MODES)}")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"rules[{index}].reason is required")

    missing = sorted(REQUIRED_PATTERNS - seen_patterns)
    for pattern in missing:
        errors.append(f"required pattern missing: {pattern}")
    return errors


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else Path("docs/hermes-upstream-sync-policy.yaml")
    errors = validate_policy_file(path)
    if errors:
        for error in errors:
            print(error)
        return 1
    print(f"policy ok: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
