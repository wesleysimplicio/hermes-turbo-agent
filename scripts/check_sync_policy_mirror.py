#!/usr/bin/env python3
"""Verify .upstream-sync-policy.yml and docs/hermes-turbo-sync-policy.json agree.

The YAML file is human-edited; the JSON is the machine-consumable mirror.
Any drift between them is a defect — this script is the CI gate that catches
it before the sync automation reads stale data.

Exits non-zero with a structured diff when the two policies diverge.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is in the dev deps
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    raise

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML = ROOT / ".upstream-sync-policy.yml"
DEFAULT_JSON = ROOT / "docs" / "hermes-turbo-sync-policy.json"


def _normalize(rule: dict) -> dict:
    """Return a comparison-friendly view of a single policy rule."""
    return {
        "name": rule.get("name"),
        "strategy": rule.get("strategy"),
        "paths": sorted(rule.get("paths") or []),
        "allow_empty_globs": sorted(rule.get("allow_empty_globs") or []),
        "allow_missing_paths": sorted(rule.get("allow_missing_paths") or []),
    }


def _index_rules(rules: list[dict]) -> dict[str, dict]:
    indexed: dict[str, dict] = {}
    for rule in rules:
        name = rule.get("name")
        if not name:
            continue
        indexed[name] = _normalize(rule)
    return indexed


def compare(yaml_path: Path, json_path: Path) -> list[str]:
    yaml_data = yaml.safe_load(yaml_path.read_text(encoding="utf-8")) or {}
    json_data = json.loads(json_path.read_text(encoding="utf-8"))

    diffs: list[str] = []

    if yaml_data.get("version") != json_data.get("version"):
        diffs.append(
            f"version drift: yaml={yaml_data.get('version')!r} json={json_data.get('version')!r}"
        )

    yaml_rules = _index_rules(yaml_data.get("rules") or [])
    json_rules = _index_rules(json_data.get("rules") or [])

    only_yaml = sorted(set(yaml_rules) - set(json_rules))
    only_json = sorted(set(json_rules) - set(yaml_rules))
    for name in only_yaml:
        diffs.append(f"rule only in YAML: {name}")
    for name in only_json:
        diffs.append(f"rule only in JSON: {name}")

    for name in sorted(set(yaml_rules) & set(json_rules)):
        y = yaml_rules[name]
        j = json_rules[name]
        for field in ("strategy", "paths", "allow_empty_globs", "allow_missing_paths"):
            if y[field] != j[field]:
                diffs.append(
                    f"{name}: {field} drift\n  yaml: {y[field]!r}\n  json: {j[field]!r}"
                )

    return diffs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--yaml", default=str(DEFAULT_YAML))
    parser.add_argument("--json", default=str(DEFAULT_JSON))
    args = parser.parse_args()

    yaml_path = Path(args.yaml).resolve()
    json_path = Path(args.json).resolve()

    if not yaml_path.exists():
        print(json.dumps({"ok": False, "error": f"missing: {yaml_path}"}, indent=2))
        return 2
    if not json_path.exists():
        print(json.dumps({"ok": False, "error": f"missing: {json_path}"}, indent=2))
        return 2

    diffs = compare(yaml_path, json_path)
    if diffs:
        print(json.dumps({"ok": False, "drifts": diffs}, indent=2))
        return 1
    print(json.dumps({"ok": True, "yaml": str(yaml_path), "json": str(json_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
