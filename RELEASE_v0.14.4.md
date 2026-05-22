# Tota Agent v0.14.4 — Hermes core sync refresh

**Release date:** 2026-05-19.  
**Previous Tota version:** `0.14.3`.

This release rebases the fork onto the latest available Hermes core that was
pulled into the local sync on May 19, 2026, while preserving the Tota-specific
performance and identity layer.

## Highlights

- **Fresh Hermes core merge.** The fork absorbs the latest upstream runtime
  changes that landed after the previous Tota sync, including gateway, browser,
  ACP, auxiliary-client, provider, UI/TUI, and docs/runtime updates.
- **Tota identity preserved.** The fork keeps `TOTA_HOME` as the primary home
  directory contract, retains the Tota branding/docs surface, and stays on the
  performance-oriented package profile (`fast`, `perf`, Rust-ready path).
- **Version alignment.** Package metadata, ACP registry metadata, and lockfile
  now align on `0.14.4`.
- **TUI regression coverage preserved.** The Tota-specific preload-skill tests
  stay in place alongside the upstream TUI update-path coverage.

## Validation target

- `python3 -m ruff check .`
- `python3 -m pytest`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
