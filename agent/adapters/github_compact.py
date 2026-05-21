"""Token-optimized adapter for `gh` CLI output.

Wraps `gh issue|pr|run` calls and returns slim JSON containing only
high-signal fields. Large bodies are replaced with short previews plus a
content-hash handle that can be re-resolved on demand via an evidence
store. Stdlib-only.

Refs #90.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from typing import Any, Dict, Iterable, List, Optional

_BODY_PREVIEW_CHARS = 240


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()[:12]


def _body_handle(body: Optional[str]) -> Dict[str, Any]:
    """Replace a long body with a preview + handle for later expansion."""
    if not body:
        return {"preview": "", "handle": None, "chars": 0}
    body_str = body.strip()
    return {
        "preview": body_str[:_BODY_PREVIEW_CHARS],
        "handle": f"body:{_hash(body_str)}",
        "chars": len(body_str),
    }


def _run_gh(args: List[str], gh_bin: str = "gh") -> str:
    """Invoke `gh` and return stdout. Raises on non-zero exit."""
    proc = subprocess.run(
        [gh_bin, *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout


def _resolve_gh(gh_bin: str) -> str:
    if shutil.which(gh_bin) is None:
        raise FileNotFoundError(f"gh binary not found: {gh_bin}")
    return gh_bin


def compact_issue(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Compact a single `gh issue view --json ...` payload."""
    return {
        "number": raw.get("number"),
        "title": raw.get("title"),
        "state": raw.get("state"),
        "url": raw.get("url"),
        "author": (raw.get("author") or {}).get("login"),
        "labels": [l.get("name") for l in (raw.get("labels") or []) if l.get("name")],
        "comments": len(raw.get("comments") or []),
        "body": _body_handle(raw.get("body")),
        "updatedAt": raw.get("updatedAt"),
    }


def compact_issue_list(raw: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compact `gh issue list --json ...` output."""
    return [
        {
            "number": i.get("number"),
            "title": i.get("title"),
            "state": i.get("state"),
            "labels": [l.get("name") for l in (i.get("labels") or []) if l.get("name")],
            "url": i.get("url"),
        }
        for i in raw
    ]


def compact_pr(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Compact `gh pr view --json ...` payload."""
    return {
        "number": raw.get("number"),
        "title": raw.get("title"),
        "state": raw.get("state"),
        "isDraft": raw.get("isDraft"),
        "url": raw.get("url"),
        "author": (raw.get("author") or {}).get("login"),
        "baseRef": raw.get("baseRefName"),
        "headRef": raw.get("headRefName"),
        "additions": raw.get("additions"),
        "deletions": raw.get("deletions"),
        "changedFiles": raw.get("changedFiles"),
        "mergeable": raw.get("mergeable"),
        "body": _body_handle(raw.get("body")),
        "reviewDecision": raw.get("reviewDecision"),
    }


def compact_pr_checks(raw: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Compact `gh pr checks --json ...` payload.

    Highlights failing checks; success checks are returned as a count only.
    """
    failing: List[Dict[str, Any]] = []
    passing = 0
    pending = 0
    for c in raw:
        state = (c.get("state") or c.get("conclusion") or "").upper()
        bucket = (c.get("bucket") or "").lower()
        is_fail = state in {"FAILURE", "FAILED", "ERROR", "TIMED_OUT"} or bucket == "fail"
        is_pending = state in {"PENDING", "IN_PROGRESS", "QUEUED"} or bucket == "pending"
        if is_fail:
            failing.append({
                "name": c.get("name"),
                "state": state or bucket,
                "url": c.get("link") or c.get("detailsUrl"),
                "workflow": c.get("workflow"),
            })
        elif is_pending:
            pending += 1
        else:
            passing += 1
    return {"failing": failing, "passing": passing, "pending": pending}


def gh_issue_compact(number: int, repo: Optional[str] = None, gh_bin: str = "gh") -> Dict[str, Any]:
    """Run `gh issue view <n> --json ...` and return the compact form."""
    _resolve_gh(gh_bin)
    args = [
        "issue", "view", str(number),
        "--json", "number,title,state,url,author,labels,comments,body,updatedAt",
    ]
    if repo:
        args += ["--repo", repo]
    return compact_issue(json.loads(_run_gh(args, gh_bin)))


def gh_pr_compact(number: int, repo: Optional[str] = None, gh_bin: str = "gh") -> Dict[str, Any]:
    """Run `gh pr view <n>` + checks and return the compact form."""
    _resolve_gh(gh_bin)
    pr_args = [
        "pr", "view", str(number),
        "--json",
        "number,title,state,isDraft,url,author,baseRefName,headRefName,"
        "additions,deletions,changedFiles,mergeable,body,reviewDecision",
    ]
    check_args = ["pr", "checks", str(number), "--json", "name,state,bucket,workflow,link"]
    if repo:
        pr_args += ["--repo", repo]
        check_args += ["--repo", repo]
    pr = compact_pr(json.loads(_run_gh(pr_args, gh_bin)))
    try:
        checks_raw = json.loads(_run_gh(check_args, gh_bin))
    except subprocess.CalledProcessError:
        checks_raw = []
    pr["checks"] = compact_pr_checks(checks_raw)
    return pr
