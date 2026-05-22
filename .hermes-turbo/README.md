# `.tota/` — Project-local Tota Agent home

This directory is the **project-local** Tota Agent home. It mirrors the
runtime layout of the user-level `$TOTA_HOME` (default `~/.tota`) so the
repository ships its own opinionated defaults.

| Path | Purpose |
| --- | --- |
| `version` | Plain-text version pin for the fork (`0.14.0`). |
| `HERMES_BASE` | Identifies the upstream Hermes baseline this fork is synced against. |
| `memories/MEMORY.md` | Seed memory entries injected into the system prompt at session start. |
| `mapped_projects.json` | Tracks which code projects have been mapped by `llm-project-mapper`. |

## Resolution order

Tota resolves its runtime home from the first match below:

1. `TOTA_HOME` environment variable
2. `HERMES_HOME` environment variable (legacy, still respected)
3. `~/.tota` (default)

This project-local `.tota/` is **not** the runtime home — it is the
authoritative source for fork-level defaults and seed data. Production
deployments copy / symlink the relevant files into the runtime home
during setup.

## Why a separate directory from `~/.tota`?

Two reasons:

- **Reviewability.** Defaults that affect every operator land in version
  control, with the same review discipline as code.
- **Profile isolation.** Operators can still keep multiple personal
  `$TOTA_HOME` profiles without forking the repository.

See `hermes_constants.py` for the runtime resolution code and
`skills/software-development/llm-project-mapper/SKILL.md` for the
mapping contract.
