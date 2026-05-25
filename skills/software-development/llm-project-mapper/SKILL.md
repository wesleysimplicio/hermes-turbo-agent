---
name: llm-project-mapper
description: Map any code project with @wesleysimplicio/llm-project-mapper before doing work, so the Hermes Turbo Agent has the AGENTS.md / INIT.md / specs / skills scaffolding it needs to ship effectively.
version: 1.0.0
author: Hermes Turbo Agent (wraps wesleysimplicio/llm-project-mapper).
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes_turbo:
    core: true
    category: software-development
    tags: [project-mapping, onboarding, agents-md, scaffolding, ralph]
    related_skills:
      - software-development/everything-code
      - software-development/spike
      - software-development/writing-plans
---

# LLM Project Mapper (Hermes Turbo Core)

The Hermes Turbo Agent treats `llm-project-mapper` as a **core onboarding step** for
any code project. Before reading source, planning, or editing, run the mapper
so the project ships an AGENTS.md ecosystem (AGENTS.md, CLAUDE.md, INIT.md,
specs, skills, CI guardrails) that every downstream tool — Hermes Turbo itself, Claude
Code, Codex, Copilot, Cursor, Aider — can pick up immediately.

## When to Use

Run the mapper the first time Hermes Turbo enters a repository, OR when the
`.hermes_turbo/mapped_projects.json` memory file does not contain a fingerprint for
the current project root. Skip if the fingerprint is fresh (< 30 days) and
the project's `AGENTS.md` still exists.

Good fits:

- onboarding into an unfamiliar codebase
- pre-flight before a multi-turn `/goal` (Ralph) loop
- before delegating to subagents that need shared context
- before generating evals or planning

Bad fits:

- one-shot shell tasks that do not touch source code
- non-code projects (raw data, design assets, ML notebooks without infra)
- temporary scratch checkouts the user has explicitly marked ephemeral

## How to Use

The skill exposes one entry-point script:

```bash
python skills/software-development/llm-project-mapper/scripts/map_project.py \
    --project-root "$PWD" \
    [--force]
```

The script:

1. Resolves `TOTA_HOME` (falling back to `HERMES_HOME` and then `~/.hermes_turbo`).
2. Reads `$TOTA_HOME/mapped_projects.json` and checks for a fingerprint of
   the project's absolute path + git remote.
3. If absent or `--force`, invokes
   `npx --yes @wesleysimplicio/llm-project-mapper` inside the project root.
   The mapper writes `AGENTS.md`, `INIT.md`, `_BOOTSTRAP.md`, the `.agents/`,
   `.claude/`, `.codex/`, `.skills/`, `.specs/` directories, and CI hooks.
4. Records the project fingerprint in `$HERMES_TURBO_HOME/mapped_projects.json` with
   the timestamp, git remote (if any), and the mapper version that ran.
5. Returns a JSON summary on stdout so the agent can decide what to read
   next (typically `AGENTS.md` and `INIT.md`).

Idempotent: re-running without `--force` is a no-op once the project is
mapped. The agent uses this idempotency to safely call the script at the
top of every coding session.

## Memory Contract

Mapped-project state lives in `$HERMES_TURBO_HOME/mapped_projects.json` so it
survives across sessions and profiles. Each entry looks like:

```json
{
  "project_root": "/abs/path/to/project",
  "git_remote": "git@github.com:org/repo.git",
  "mapped_at": "2026-05-18T00:00:00Z",
  "mapper_version": "0.2.0",
  "agents_md_present": true,
  "ralph_ready": true
}
```

`ralph_ready` is `true` when the mapping produced `AGENTS.md`, `INIT.md`,
and `_BOOTSTRAP.md` — the minimum surface a `/goal` (Ralph) loop needs to
make non-trivial progress without re-onboarding mid-flight. The mapper
also writes `CLAUDE.md`, `README` mirrors, and the `.agents/`, `.claude/`,
`.codex/`, `.skills/` directories; those vary across mapper versions, so
the readiness check stays on the three docs above.

## Why This Lives in Hermes Turbo Core

Hermes Turbo Agent is a *modified, faster Hermes*. Speed comes from never paying the
onboarding tax twice: the mapper canonicalizes the project once, the memory
file remembers it forever, and every subsequent invocation skips straight to
work. This is the same idea as the upstream `/goal` Ralph loop, applied at
the project layer instead of the turn layer.
