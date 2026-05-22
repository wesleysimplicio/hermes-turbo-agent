from __future__ import annotations

from pathlib import Path

from scripts.sync_hermes_upstream import (
    _fetch_upstream_ref,
    classify_path,
    load_policy,
    render_sync_report,
)


def test_classify_path_uses_most_specific_sync_policy_rule():
    policy = load_policy(Path(__file__).resolve().parents[2] / "docs" / "hermes-upstream-sync-policy.yaml")

    token_saver = classify_path("plugins/token_saver/token_saver.py", policy)
    unknown = classify_path("agent/new_upstream_file.py", policy)

    assert token_saver.mode == "keep-turbo"
    assert token_saver.pattern == "plugins/token_saver/**"
    assert unknown.mode == "merge"


def test_render_sync_report_includes_reapply_and_validation_sections():
    policy = load_policy(Path(__file__).resolve().parents[2] / "docs" / "hermes-upstream-sync-policy.yaml")

    report = render_sync_report(
        policy=policy,
        upstream_ref="upstream/main",
        branch_name="codex/hermes-upstream-sync-20260519",
        upstream_commits=["abc123 fix upstream bug", "def456 add provider"],
        changed_paths=["plugins/token_saver/token_saver.py", "agent/new_upstream_file.py"],
        conflicts=["README.md"],
    )

    assert "abc123 fix upstream bug" in report
    assert "plugins/token_saver/token_saver.py" in report
    assert "keep-turbo" in report
    assert "README.md" in report
    assert "taskflow run ." in report


def test_fetch_upstream_ref_fetches_only_the_requested_branch(monkeypatch, tmp_path):
    calls = []

    def fake_run_git(args, *, cwd):
        calls.append((args, cwd))
        return ""

    monkeypatch.setattr("scripts.sync_hermes_upstream.run_git", fake_run_git)

    _fetch_upstream_ref(
        tmp_path,
        remote_name="hermes-upstream",
        upstream_ref="hermes-upstream/main",
    )

    assert calls == [(["fetch", "--quiet", "hermes-upstream", "main"], tmp_path)]
