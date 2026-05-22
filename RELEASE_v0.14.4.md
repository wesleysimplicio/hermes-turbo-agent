# Hermes Turbo Agent v0.14.4 — Hermes core sync refresh

**Release date:** 2026-05-19.  
**Previous Hermes Turbo version:** `0.14.3`.

This release rebases the fork onto the latest available Hermes core that was
pulled into the local sync on May 19, 2026, while preserving the Hermes Turbo-specific
performance and identity layer.

## Highlights

- **Fresh Hermes core merge.** The fork absorbs the latest upstream runtime
  changes that landed after the previous Hermes Turbo sync, including gateway, browser,
  ACP, auxiliary-client, provider, UI/TUI, and docs/runtime updates.
- **Hermes Turbo identity preserved.** The fork keeps `HERMES_TURBO_HOME` as the primary home
  directory contract, retains the Hermes Turbo branding/docs surface, and stays on the
  performance-oriented package profile (`fast`, `perf`, Rust-ready path).
- **Version alignment.** Package metadata, ACP registry metadata, and lockfile
  now align on `0.14.4`.
- **TUI regression coverage preserved.** The Hermes Turbo-specific preload-skill tests
  stay in place alongside the upstream TUI update-path coverage.

## Validation target

- `python3 -m ruff check .`
- `python3 -m pytest`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/hermes-turbo-agent-main`
