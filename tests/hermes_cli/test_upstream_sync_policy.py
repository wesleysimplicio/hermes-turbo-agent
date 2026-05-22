from __future__ import annotations

from pathlib import Path

from scripts.validate_hermes_sync_policy import validate_policy_file


def test_upstream_sync_policy_is_machine_readable_and_covers_turbo_owned_paths():
    policy_path = Path(__file__).resolve().parents[2] / "docs" / "hermes-upstream-sync-policy.yaml"

    errors = validate_policy_file(policy_path)

    assert errors == []
