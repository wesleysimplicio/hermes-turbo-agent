Tota Agent is a modified, faster Hermes — built on Nous Research's Hermes Agent, synced against v0.14.0. Same surface as Hermes, lower latency, tighter project on-ramps.
§
For any code project, run the `llm-project-mapper` skill first (script: `skills/software-development/llm-project-mapper/scripts/map_project.py`). It is idempotent and records mapped projects in `$TOTA_HOME/mapped_projects.json`. Skip only if the project has a fresh entry (< 30 days) and `AGENTS.md` still exists.
§
Tota home resolution honors `TOTA_HOME` first, then legacy `HERMES_HOME`, then `~/.tota`. Subprocess spawners must propagate `TOTA_HOME` explicitly when running outside the parent shell.
§
Project-local Tota defaults live in the repo's `.tota/` directory. Runtime home is `$TOTA_HOME` (default `~/.tota`).
