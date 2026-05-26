# Autonomous Coding Instructions

You are an autonomous coding agent.

## Read First

- PRD.md
- PROGRESS.md
- README.md
- AGENTS.md
- tests
- project/package files

## Work Loop

1. Pick the next incomplete task.
2. Implement the smallest safe change.
3. Run validation.
4. Fix failures.
5. Update PROGRESS.md.
6. Continue until complete.

## Do Not

- rewrite unrelated architecture
- remove tests
- fake successful validation
- push without explicit instruction
- expose secrets
- modify production credentials

## Complete Only When

- PRD.md is fully done
- tests/build/lint pass
- GOAL_RESULT.md is written

<!-- rtk-cli:start -->
## Shell token-smart (RTK CLI, optional)

If `rtk` (https://github.com/rtk-ai/rtk) is on PATH, prefer it for shell-heavy and exploratory work — compact output, ~40-70% fewer tokens, same signal.

```bash
rtk read AGENTS.md
rtk grep "pattern" hermes_cli/
rtk find "*.py" .
rtk git status
rtk git diff
rtk git log -n 10
rtk pytest
```

Rules:

- Use `rtk read|grep|find|git ...` as first choice for textual inspection.
- Use `rtk <command>` on verbose validators where a summary is enough.
- **Do not** route through RTK: interactive prompts, streaming, evidence-bearing output.
- If `rtk` is not installed, fall back to plain commands — no hard dependency.

See `.skills/rtk-cli/SKILL.md` for the full skill manifest.
<!-- rtk-cli:end -->

<!-- yool-tuple-hamt:start -->
## yool / tuple / HAMT (capability addressing)

Spec: https://github.com/wesleysimplicio/yool-tuple-hamt (v0.2).

Every agent registered in this repo SHOULD declare its capability with the following fields:

```markdown
### My Agent

- yool_id: `agent.dev.python`
- authority: dev | ops | review | audit
- lane: fast | slow | background
- agent_terms:
    cpu_quota_pct: 60       # MANDATORY guardrail (spec §11.1)
    disk_quota_mb: 100      # MANDATORY guardrail (spec §11.2)
    timeout_s: 300
```

Guardrails are MANDATORY per Victor Genaro's review: *"precisa de guardrail pra não fritar o processador. Você precisa de garbage collector também pra não encher 100% do disco."* See spec §11.
<!-- yool-tuple-hamt:end -->

<!-- codex-long-running-agent-overlay:start -->
## Universal Long-Running Agent Overlay

This section complements the repository-specific guidance already in this file. If anything here conflicts with the repo-specific rules above, the repo-specific rules win.

- `PRD.md` is the task source of truth for long-running sessions.
- `PROGRESS.md` is the persistent checkpoint log.
- `GOAL_RESULT.md` is the final execution report.
- Before coding, read this file, `PRD.md`, `PROGRESS.md` when it exists, `README.md`, project manifests, tests, and the relevant source folders.
- Work in small checkpoints, run the smallest relevant validation after each meaningful change, update `PROGRESS.md`, and continue until complete or genuinely blocked.
- Stop only when the requested work is complete, validation is documented, and `GOAL_RESULT.md` reflects the outcome.
- Do not rewrite unrelated architecture, fake successful validation, expose secrets, or push without explicit operator instruction for the active session.
<!-- codex-long-running-agent-overlay:end -->
