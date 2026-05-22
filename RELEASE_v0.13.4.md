# Tota Agent v0.13.4

Date: 2026-05-18

## Added

- Added `scripts/tota_hermes_daily_update.py`, a daily automation routine that
  creates an isolated checkout, runs `hermes update`, merges
  `NousResearch/hermes-agent` upstream, rebuilds on Python `3.14.5`, validates
  Tota performance customizations, and pushes a dated sync branch when clean.
- Added `scripts/install_tota_hermes_daily_update_launchd.py` to install the
  macOS LaunchAgent for the daily sync.
- Added `docs/tota-hermes-daily-update.md` with operation, install, dry-run,
  uninstall, and failure-handling instructions.

## Environment

- Updated the local machine's Homebrew `uv` to `0.11.14`.
- Updated the local machine's Homebrew `python@3.14` to `3.14.5`.
- Installed Python `3.14.5` through `uv python install` for reproducible Tota
  virtual environments.
