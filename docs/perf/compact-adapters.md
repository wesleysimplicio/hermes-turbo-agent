# Compact GitHub & CI Adapters

Token-optimized wrappers for `gh` CLI output and CI logs. They turn the
high-volume `gh issue/pr view`, `gh pr checks`, and `gh run view --log`
streams into slim JSON payloads suitable for direct inclusion in an
agent prompt.

## Modules

- `agent/adapters/github_compact.py` — wraps `gh` invocations and
  returns only high-signal fields (number, title, state, url, labels,
  diff stats, etc.). Long issue/PR bodies are replaced with a
  240-character preview plus a `body:<sha1>` handle that points to the
  full body in the evidence store.
- `agent/adapters/ci_compact.py` — parses raw CI log text and returns
  only the failing stages (job + step) with a short excerpt of the
  first error and a signature line. Strips `##[group]` markers,
  progress bars, debug output and other low-signal noise.

## Usage

```python
from agent.adapters.github_compact import gh_issue_compact, gh_pr_compact
from agent.adapters.ci_compact import parse_ci_log

issue = gh_issue_compact(90, repo="wesleysimplicio/hermes-turbo-agent")
pr = gh_pr_compact(115, repo="wesleysimplicio/hermes-turbo-agent")
log = open("run.log").read()
summary = parse_ci_log(log)
```

## Output shape

`gh_issue_compact`:

```json
{
  "number": 90,
  "title": "...",
  "state": "OPEN",
  "url": "...",
  "author": "alice",
  "labels": ["perf"],
  "comments": 3,
  "body": {"preview": "first 240 chars...", "handle": "body:abc123", "chars": 2000},
  "updatedAt": "2024-05-20T12:00:00Z"
}
```

`parse_ci_log`:

```json
{
  "failing": [{
    "job": "build",
    "step": "pytest",
    "first_error_line": 142,
    "excerpt": "##[error]AssertionError...",
    "signature": "AssertionError: expected 1 got 2"
  }],
  "stats": {"total_lines": 4321, "stages_seen": 7, "stages_failing": 1}
}
```

## Design notes

- Stdlib only. No new dependencies.
- Body handles are content-addressed (`sha1[:12]`) so identical bodies
  collapse to the same handle across runs.
- The CI parser is permissive: it accepts the tab-delimited GHA log
  format as well as plain log lines from any CI.
- Errors are detected by a curated marker regex (`error`, `fatal`,
  `traceback`, `##[error]`, `E   ` etc.) plus a `FAIL` keyword. The
  excerpt is capped at 5 lines per stage so a 50k-line stack trace
  collapses to a handful of bytes.

Refs #90.
