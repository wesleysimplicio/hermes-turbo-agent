Hermes Turbo Agent is a modified, faster Hermes — built on Nous Research's Hermes Agent, synced against v0.14.0. Same surface as Hermes, lower latency, tighter project on-ramps.
§
For any code project, run the `llm-project-mapper` skill first (script: `skills/software-development/llm-project-mapper/scripts/map_project.py`). It is idempotent and records mapped projects in `$HERMES_TURBO_HOME/mapped_projects.json`. Skip only if the project has a fresh entry (< 30 days) and `AGENTS.md` still exists.
§
Hermes Turbo home resolution honors `HERMES_TURBO_HOME` first, then legacy `HERMES_HOME`, then `~/.hermes-turbo`. Subprocess spawners must propagate `HERMES_TURBO_HOME` explicitly when running outside the parent shell.
§
Project-local Hermes Turbo defaults live in the repo's `.hermes-turbo/` directory. Runtime home is `$HERMES_TURBO_HOME` (default `~/.hermes-turbo`).
