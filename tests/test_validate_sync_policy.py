from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "validate_sync_policy.py"


def load_module():
    spec = importlib.util.spec_from_file_location("validate_sync_policy_test", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_sync_policy_test"] = module
    spec.loader.exec_module(module)
    return module


def test_validate_policy_accepts_existing_paths(tmp_path):
    mod = load_module()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "existing.md").write_text("ok", encoding="utf-8")
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "docs",
                        "strategy": "keep-turbo",
                        "paths": ["docs/existing.md"]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert mod.validate_policy(policy, tmp_path) == []


def test_validate_policy_rejects_missing_path(tmp_path):
    mod = load_module()
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "missing",
                        "strategy": "merge",
                        "paths": ["README.md"]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    errors = mod.validate_policy(policy, tmp_path)
    assert any("missing path: README.md" in error for error in errors)


def test_validate_policy_allows_empty_glob_when_declared(tmp_path):
    mod = load_module()
    (tmp_path / "docs").mkdir()
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "generated",
                        "strategy": "regenerate",
                        "paths": ["docs/generated/*.png"],
                        "allow_empty_globs": ["docs/generated/*.png"]
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert mod.validate_policy(policy, tmp_path) == []
