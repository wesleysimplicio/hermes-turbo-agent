"""Unit tests for agent.adapters.ci_compact."""

from __future__ import annotations

from agent.adapters.ci_compact import parse_ci_log, summarize_runs


GHA_NOISY_LOG = """\
build\tCheckout\t2024-05-20T12:00:00.000Z ##[group]Run actions/checkout@v4
build\tCheckout\t2024-05-20T12:00:00.100Z Receiving objects: 12% (120/1000)
build\tCheckout\t2024-05-20T12:00:00.200Z Receiving objects: 100% (1000/1000)
build\tCheckout\t2024-05-20T12:00:00.300Z ##[endgroup]
build\tpytest\t2024-05-20T12:00:01.000Z Running 42 tests
build\tpytest\t2024-05-20T12:00:01.500Z test_foo PASSED
build\tpytest\t2024-05-20T12:00:02.000Z test_bar FAILED
build\tpytest\t2024-05-20T12:00:02.100Z ##[error]AssertionError: expected 1 got 2
build\tpytest\t2024-05-20T12:00:02.200Z   File "x.py", line 10, in test_bar
build\tpytest\t2024-05-20T12:00:02.300Z     assert 1 == 2
e2e\tplaywright\t2024-05-20T12:00:05.000Z 12 passed in 30s
"""


def test_parse_ci_log_returns_only_failing_stages():
    out = parse_ci_log(GHA_NOISY_LOG)
    assert out["stats"]["stages_failing"] == 1
    assert len(out["failing"]) == 1
    failing = out["failing"][0]
    assert failing["job"] == "build"
    assert failing["step"] == "pytest"
    assert "AssertionError" in failing["signature"]
    assert failing["first_error_line"] > 0
    assert "AssertionError" in failing["excerpt"]


def test_parse_ci_log_strips_progress_and_groups():
    out = parse_ci_log(GHA_NOISY_LOG)
    for stage in out["failing"]:
        assert "Receiving objects" not in stage["excerpt"]
        assert "##[group]" not in stage["excerpt"]


def test_parse_ci_log_plain_text():
    text = "running tests\nTraceback (most recent call last):\n  File x\nFAIL\nok\n"
    out = parse_ci_log(text)
    assert out["stats"]["stages_failing"] == 1
    assert out["failing"][0]["job"] is None
    assert "Traceback" in out["failing"][0]["signature"]


def test_parse_ci_log_excerpt_capped():
    lines = ["job\tstep\t2024-05-20T12:00:00Z error number {}".format(i)
             for i in range(50)]
    out = parse_ci_log("\n".join(lines))
    assert out["stats"]["stages_failing"] == 1
    assert out["failing"][0]["excerpt"].count("\n") < 50


def test_parse_ci_log_clean_returns_empty():
    text = "Run pytest\ntest_a PASSED\ntest_b PASSED\nDone.\n"
    out = parse_ci_log(text)
    assert out["failing"] == []
    assert out["stats"]["stages_failing"] == 0


def test_summarize_runs_keeps_only_failed():
    raw = [
        {"databaseId": 1, "name": "ci", "conclusion": "success",
         "headBranch": "main", "url": "u1", "createdAt": "2024-05-20T12:00:00Z"},
        {"databaseId": 2, "name": "ci", "conclusion": "failure",
         "headBranch": "feat/x", "url": "u2", "createdAt": "2024-05-20T13:00:00Z"},
        {"databaseId": 3, "name": "ci", "conclusion": "cancelled",
         "headBranch": "feat/y", "url": "u3", "createdAt": "2024-05-20T14:00:00Z"},
        {"id": 4, "workflowName": "ci", "status": "in_progress",
         "headBranch": "main", "url": "u4"},
    ]
    out = summarize_runs(raw)
    ids = [r["id"] for r in out]
    assert ids == [2, 3, 4]
