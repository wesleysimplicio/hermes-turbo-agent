# Hermes Turbo Agent v0.14.3 — Installed-user update prompt

**Release date:** 2026-05-18.
**Previous Hermes Turbo version:** `0.14.2`.

This release makes the Hermes Turbo update path part of the installed product instead
of only an operator-side maintenance script.

## Highlights

- **Interactive update prompt.** On agent-starting commands, Hermes Turbo checks the
  latest `wesleysimplicio/hermes-turbo-agent` GitHub Release and asks the user whether
  to update when a newer release exists.
- **Safe startup behavior.** The prompt only runs on interactive TTY sessions,
  is cached, and can be disabled with `HERMES_TURBO_SKIP_UPDATE_PROMPT=1` or
  `HERMES_TURBO_UPDATE_PROMPT=0`.
- **Install-aware update command.** Git checkouts call the project update path;
  packaged installs fall back to installing from the Hermes Turbo GitHub repository.
- **Release metadata sync.** Package metadata, ACP registry metadata, and
  `.hermes-turbo/version` are aligned to `0.14.3`.

## Validation

- `python -m pytest -o addopts='' tests/hermes_cli/test_hermes_turbo_update_prompt.py tests/test_cli_startup_gating.py tests/acp/test_registry_manifest.py tests/test_hermes_turbo_brand_pass.py -q --tb=short`
- `uv lock --check`
- `git diff --check --ignore-submodules`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/hermes-turbo-agent-main`
