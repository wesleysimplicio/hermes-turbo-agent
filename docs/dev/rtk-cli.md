# RTK CLI — token-smart shell primer

`rtk` (https://github.com/rtk-ai/rtk) is an **optional** wrapper that produces compact,
agent-friendly output for common shell verbs (`read`, `grep`, `find`, `git`, `npm`,
`pytest`). It cuts ~40-70% of tokens during exploration and verbose validation
without losing technical signal.

This repo does **not** depend on RTK. If it's missing, every command falls back to
its plain equivalent.

## Install

Follow upstream instructions: https://github.com/rtk-ai/rtk

After install, confirm with:

```bash
scripts/check-rtk.sh
```

The script exits 0 and prints the resolved binary if `rtk` is on `PATH`; otherwise
it exits 1 with a hint pointing back to upstream.

## When to prefer RTK

| Goal | Plain | RTK |
| --- | --- | --- |
| Read a short file | `cat AGENTS.md` | `rtk read AGENTS.md` |
| Search a pattern | `grep -rn "x" hermes_cli/` | `rtk grep "x" hermes_cli/` |
| Find files | `find . -name "*.py"` | `rtk find "*.py" .` |
| Repo status | `git status` | `rtk git status` |
| Diff | `git diff` | `rtk git diff` |
| Short history | `git log -n 10` | `rtk git log -n 10` |
| Smoke tests | `pytest -q` | `rtk pytest` |

## When NOT to use RTK

- Interactive prompts (`gh auth login`, `npm init`).
- Streaming output (`tail -f`, `gh run watch`).
- Evidence-bearing output that must stay verbatim (Playwright traces, screenshots,
  stack traces attached to issues/PRs).
- Pipes consumed by another process (output shape matters).

## Related

- Skill manifest: `.skills/rtk-cli/SKILL.md`
- Agent guidance: `AGENTS.md` -> section "Shell token-smart (RTK CLI, optional)"
- Detection script: `scripts/check-rtk.sh`
