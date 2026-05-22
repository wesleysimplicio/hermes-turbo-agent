# Tota Agent v0.14.3 — Installed-user update prompt

**Release date:** 2026-05-18.
**Previous Tota version:** `0.14.2`.

This release makes the Tota update path part of the installed product instead
of only an operator-side maintenance script.

## Highlights

- **Interactive update prompt.** On agent-starting commands, Tota checks the
  latest `wesleysimplicio/tota-agent` GitHub Release and asks the user whether
  to update when a newer release exists.
- **Safe startup behavior.** The prompt only runs on interactive TTY sessions,
  is cached, and can be disabled with `TOTA_SKIP_UPDATE_PROMPT=1` or
  `TOTA_UPDATE_PROMPT=0`.
- **Install-aware update command.** Git checkouts call the project update path;
  packaged installs fall back to installing from the Tota GitHub repository.
- **Release metadata sync.** Package metadata, ACP registry metadata, and
  `.tota/version` are aligned to `0.14.3`.

## Validation

- `python -m pytest -o addopts='' tests/hermes_cli/test_tota_update_prompt.py tests/test_cli_startup_gating.py tests/acp/test_registry_manifest.py tests/test_tota_brand_pass.py -q --tb=short`
- `uv lock --check`
- `git diff --check --ignore-submodules`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
