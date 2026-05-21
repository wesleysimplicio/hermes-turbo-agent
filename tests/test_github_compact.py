"""Unit tests for agent.adapters.github_compact."""

from __future__ import annotations

from agent.adapters.github_compact import (
    compact_issue,
    compact_issue_list,
    compact_pr,
    compact_pr_checks,
)


def test_compact_issue_keeps_only_high_signal_fields():
    raw = {
        "number": 90,
        "title": "Add adapters",
        "state": "OPEN",
        "url": "https://github.com/x/y/issues/90",
        "author": {"login": "alice", "email": "alice@example.com", "bio": "..."},
        "labels": [{"name": "perf"}, {"name": "tooling"}, {"color": "f00"}],
        "comments": [{"id": 1}, {"id": 2}, {"id": 3}],
        "body": "x" * 2000,
        "updatedAt": "2024-05-20T12:00:00Z",
        "extraNoise": "drop me",
    }
    out = compact_issue(raw)
    assert out["number"] == 90
    assert out["author"] == "alice"
    assert out["labels"] == ["perf", "tooling"]
    assert out["comments"] == 3
    assert out["body"]["chars"] == 2000
    assert len(out["body"]["preview"]) <= 240
    assert out["body"]["handle"].startswith("body:")
    assert "extraNoise" not in out


def test_compact_issue_handles_missing_body_and_author():
    out = compact_issue({"number": 1, "title": "t", "state": "OPEN"})
    assert out["body"] == {"preview": "", "handle": None, "chars": 0}
    assert out["author"] is None
    assert out["labels"] == []
    assert out["comments"] == 0


def test_compact_issue_list_minifies():
    raw = [
        {"number": 1, "title": "a", "state": "OPEN", "labels": [{"name": "bug"}],
         "url": "u1", "body": "x" * 10_000},
        {"number": 2, "title": "b", "state": "CLOSED", "labels": [], "url": "u2"},
    ]
    out = compact_issue_list(raw)
    assert out == [
        {"number": 1, "title": "a", "state": "OPEN", "labels": ["bug"], "url": "u1"},
        {"number": 2, "title": "b", "state": "CLOSED", "labels": [], "url": "u2"},
    ]


def test_compact_pr_preserves_diff_stats_and_drops_body():
    raw = {
        "number": 115,
        "title": "feat: x",
        "state": "OPEN",
        "isDraft": True,
        "url": "https://...",
        "author": {"login": "bob"},
        "baseRefName": "main",
        "headRefName": "feat/x",
        "additions": 120,
        "deletions": 30,
        "changedFiles": 4,
        "mergeable": "MERGEABLE",
        "body": "long " * 500,
        "reviewDecision": "REVIEW_REQUIRED",
    }
    out = compact_pr(raw)
    assert out["additions"] == 120 and out["deletions"] == 30
    assert out["baseRef"] == "main" and out["headRef"] == "feat/x"
    assert out["body"]["chars"] > 240
    assert out["body"]["handle"]


def test_compact_pr_checks_buckets_states():
    raw = [
        {"name": "lint", "state": "SUCCESS", "bucket": "pass"},
        {"name": "unit", "state": "FAILURE", "bucket": "fail",
         "link": "u", "workflow": "ci"},
        {"name": "e2e", "state": "IN_PROGRESS", "bucket": "pending"},
        {"name": "build", "conclusion": "TIMED_OUT"},
    ]
    out = compact_pr_checks(raw)
    assert out["passing"] == 1
    assert out["pending"] == 1
    assert len(out["failing"]) == 2
    names = {f["name"] for f in out["failing"]}
    assert names == {"unit", "build"}
