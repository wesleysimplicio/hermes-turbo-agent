# Tota Agent Daily Hermes Update

Tota Agent is a performance-focused fork of Hermes Agent. The daily update
routine keeps the Hermes core fresh while preserving Tota's speed and branding
customizations.

## What Runs Daily

The LaunchAgent runs:

```bash
python3 scripts/tota_hermes_daily_update.py \
  --repo /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent \
  --python-version 3.14.5
```

The routine:

1. Creates an isolated checkout under `~/.local/state/tota-agent/hermes-sync/`.
2. Starts from `origin/main`.
3. Installs or refreshes Python `3.14.5` with `uv`.
4. Runs `hermes update --yes --no-backup` inside the isolated worktree.
5. Merges `upstream/main` from `NousResearch/hermes-agent`.
6. Verifies Tota-specific markers such as `TOTA_HOME`, `orjson`, `msgspec`,
   and the Tota README identity.
7. Runs focused validation plus `taskflow run`.
8. Validates `docs/hermes-turbo-sync-policy.json` with `scripts/validate_sync_policy.py`.
9. Refreshes benchmark JSON first, then regenerates Markdown/PDF/cards with `scripts/refresh_sync_benchmarks.py`.
10. Writes `docs/benchmark-refresh-status.{json,md}` and marks claims stale when refresh cannot complete.
11. Stores a ready-to-paste PR body snippet with measured benchmark deltas in `latest_pr_body.md`.
12. Commits and pushes a dated `codex/tota-hermes-daily-*` branch when all
   checks pass.

If a merge conflict happens, the routine stops and writes the conflicted file
list to:

```bash
~/.local/state/tota-agent/hermes-sync/latest.md
```

It does not overwrite local customizations silently.

The isolated checkout has `git rerere` enabled. After a human resolves the first
conflict set, Git can reuse those recorded resolutions on later daily syncs.

## Install The Daily Job

```bash
cd /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent
python3 scripts/install_tota_hermes_daily_update_launchd.py --hour 6 --minute 30
```

Run once immediately:

```bash
python3 scripts/tota_hermes_daily_update.py --repo . --python-version 3.14.5
```

Dry-run without commit/push:

```bash
python3 scripts/tota_hermes_daily_update.py --repo . --python-version 3.14.5 --dry-run
```

Uninstall the daily job:

```bash
python3 scripts/install_tota_hermes_daily_update_launchd.py --uninstall
```

## Python Policy

The current target is Python `3.14.5`, verified from python.org as the latest
stable Python 3 release on May 18, 2026. The machine also keeps Homebrew
`python@3.14` and `uv` updated so Tota can rebuild `.venv` environments from a
fresh interpreter.

If a dependency is not ready for the newest Python yet, the routine fails in the
isolated checkout and leaves the current working checkout alone.
