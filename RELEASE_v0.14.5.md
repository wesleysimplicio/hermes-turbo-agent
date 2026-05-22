# Hermes Turbo Agent v0.14.5 — rename + desktop/car profile distributions

**Release type:** fork identity refresh.

**Previous version:** `0.14.4`.

This release promotes the Tota fork into the `Hermes Turbo Agent` identity
while preserving runtime compatibility with existing `.tota`, `TOTA_HOME`,
legacy docs, and the older benchmark package.

## Highlights

- **New primary brand:** `Hermes Turbo Agent` is now the main user-facing name
  in package metadata, prompt identity, ACP metadata, and the top-level README.
- **New CLI aliases:** `hermes-turbo`, `hermes-turbo-agent`, and
  `hermes-turbo-acp` now resolve to the same runtime entrypoints as the legacy
  `tota*` aliases.
- **Desktop profile distribution:** installable local operator profile focused
  on coding, browser work, desktop automation, and release execution.
- **Car profile distribution:** installable voice-first copilot profile for
  route-aware capture, summaries, and hands-free task orchestration.
- **Compatibility-first home envs:** `HERMES_TURBO_HOME` is now supported and
  wins over `TOTA_HOME`, while the default storage path remains `~/.tota` for
  zero-migration upgrades.

## Validation

- `python -m pytest tests/test_hermes_constants.py -q`
- `python -m pytest tests/test_subprocess_home_isolation.py -q`
- `python -m ruff check hermes_constants.py agent/prompt_builder.py`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
