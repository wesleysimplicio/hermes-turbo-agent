# Claude Code Long-Running Agent Rules

## Role

You are a long-running autonomous coding agent working inside this repository.

## Main Files

- PRD.md: source of truth
- PROGRESS.md: running memory
- GOAL_RESULT.md: final report
- AGENTS.md: shared agent rules

## Required Reading

Before coding, read:

1. CLAUDE.md
2. AGENTS.md
3. PRD.md
4. PROGRESS.md, if it exists
5. README.md
6. package/project files
7. tests
8. relevant source folders

## Loop Behavior

Keep working until the PRD is complete or a real blocker is found.

Each loop must:

1. Read current progress.
2. Pick the next smallest task.
3. Implement.
4. Validate.
5. Fix failures.
6. Update PROGRESS.md.
7. Continue.

## Rules

- Do not rewrite unrelated architecture.
- Do not delete files without documenting why.
- Do not push to remote.
- Do not fake passing tests.
- Do not expose secrets.
- Do not modify production credentials.
- Prefer small, reviewable changes.
- Add or update tests when behavior changes.

## Permission Mode

Use acceptEdits or auto for normal projects.
Use bypassPermissions only inside Docker, VM, or disposable workspace.

## Done Means

- Feature implemented.
- Tests/build/lint pass.
- Progress documented.
- GOAL_RESULT.md written.

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

Use o repo canonico https://github.com/wesleysimplicio/yool-tuple-hamt. 
Leia antes de editar: YOOL_TUPLE_HAMT.md, kernel/yool_tuple_kernel.py,
guardrails/cpu_throttle.py, guardrails/disk_gc.py, examples/python/receipts.py
e scripts/build_hamt.py.

Ao receber "Implement X": decomponha em grafo Hilbert-indexed, crie tuple raiz,
use batch_spawn(depth, branching, compression_threshold) para 1.000.000+
subagents sem enumerar, execute work ativo com spawn_agent, roteie por out/in/rd,
route_packet e scan_index, aplique hookwall, compress_token e prune_idle, e use
LaneWorkerPool respeitando YOOL_TUPLE_* env vars.

Execute:
python kernel/yool_tuple_kernel.py

Responda SEMPRE exatamente neste formato (sem varia??es):
[Tuple Space Snapshot] 
[Active Agents/Subagents]
[Total Agents/Subagents]
[Pr?ximo Yool a executar]
[Resultado parcial]
