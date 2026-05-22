# Hermes Turbo Agent v0.14.6 — public identity polish

**Release type:** brand polish and compatibility cleanup.

**Previous version:** `0.14.5`.

This release completes the visible rename pass after the Tota-to-Hermes Turbo
transition. Legacy `tota*` commands, `TOTA_HOME`, and `.tota` storage remain
supported for existing installations, but new public copy now leads with
`Hermes Turbo Agent`.

## Highlights

- **Agent guide rename:** `AGENTS.md` now presents Hermes Turbo Agent as the
  canonical project name and documents `HERMES_TURBO_HOME` as the preferred
  home override.
- **README cleanup:** local checkout instructions, performance extras, daily
  sync copy, and release notes now use Hermes Turbo Agent terminology.
- **Runtime wording cleanup:** update prompts and CLI skins now display Hermes
  Turbo Agent instead of Tota Agent.
- **Sync routine cleanup:** the daily upstream sync routine now points at
  `wesleysimplicio/hermes-turbo-agent`, writes state under
  `~/.local/state/hermes-turbo-agent/`, and validates the Hermes Turbo identity.
- **Microsite polish:** the HTML landing page leads with desktop/car profiles
  and keeps Tota references only as compatibility context.

## Validation

- `python -m ruff check hermes_cli/__init__.py hermes_cli/tota_update_prompt.py hermes_cli/skin_engine.py scripts/tota_hermes_daily_update.py`
- `python -m pytest tests/test_hermes_constants.py tests/test_subprocess_home_isolation.py -q`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
