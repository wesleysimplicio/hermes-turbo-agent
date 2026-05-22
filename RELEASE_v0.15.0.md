# Hermes Turbo Agent v0.15.0 — Rebranding + upstream sync hardening

**Release type:** Identity rename + sync-system hardening (minor bump for public-surface change).
**Previous version:** `0.14.2`.

This release closes two work streams: a complete removal of the legacy
"Tota Agent" identity in favor of **Hermes Turbo Agent**, and the
follow-through on the audit gaps in the daily upstream sync system that
was introduced in 0.14.x (issues #85, #86, #87).

## Breaking changes — operator action required

The fork-native environment variable and home directory have been renamed.
There is **no automatic fallback**. Operators upgrading from 0.14.x must
migrate manually:

```bash
# Environment
sed -i 's/TOTA_HOME/HERMES_TURBO_HOME/g' ~/.profile ~/.zshrc /etc/environment

# Data directory (one-time)
mv ~/.tota ~/.hermes-turbo

# Project-local defaults (per checkout, if you keep one)
mv .tota .hermes-turbo
```

Legacy `HERMES_HOME` is still honored as a secondary fallback (unchanged
from prior releases). Only the fork-native `TOTA_HOME` has been removed.

Console script aliases changed too:

| Old | New |
|---|---|
| `tota` | `hermes-turbo` |
| `tota-agent` | `hermes-turbo-agent` |
| `tota-acp` | `hermes-turbo-acp` |

The `hermes` and `hermes-agent` aliases continue to work unchanged.

## Identity removal

Every fork-native surface that previously said *Tota Agent* now says
*Hermes Turbo Agent*. This covers:

- `pyproject.toml` description, console_scripts, version
- Python identifiers: `_tota_home` → `_hermes_turbo_home`,
  `_resolve_tota_home_fallback`, `_assert_tota_personality`,
  `bootstrap_tota_home`, `fresh_tota_home`, `tota_map_project`
- Env vars: `TOTA_HOME`, `TOTA_AUTO_MAP`, `TOTA_FAST_STATE`,
  `TOTA_GATEWAY_SIDECAR`, `TOTA_AGENT_*` → `HERMES_TURBO_*`
- Paths: `.tota/`, `~/.tota`, `docs/assets/tota-{brand,benchmark,social}/`,
  `tota_agent_benchmark_report.pdf`, `tota-agent.html`,
  `docs/tota-{benchmark,identity-customization,social-storyboard}.md`,
  `scripts/{tota_,install_tota_,generate_tota_,benchmark_tota_}*`
- Asset filenames: all `tota-agent-*.{png,svg,jpg}` renamed (no image
  regeneration in this release — visual text inside artwork still reads
  "Tota Agent" until the next art pass; see TODO in
  `docs/hermes-turbo-identity-customization.md`)
- Brand SVG aria-labels and inline benchmark caption text
- Release notes 0.13.x and 0.14.x rewritten retroactively to use the new
  name (historical archive flows from the canonical brand, not the legacy
  one)

The 0.13.x and 0.14.x release notes still describe what was shipped at
those points in time; only the brand string changed. Commit history is
unchanged.

## Upstream sync hardening (issue follow-ups to #85/#86/#87)

### Policy coverage (`.upstream-sync-policy.yml` and its JSON mirror)

Three new rules close the gap discovered by the audit (~76 fork-owned
files had no explicit ownership):

- `fork-infrastructure-and-manifests` (strategy: `merge`) —
  `pyproject.toml`, `package.json`, `package-lock.json`, `uv.lock`,
  `Dockerfile`, `docker-compose.yml`, `flake.nix`, `flake.lock`,
  `MANIFEST.in`, `constraints-termux.txt`, `cli-config.yaml.example`.
- `fork-owned-modules` (strategy: `keep-turbo`) — `rust_ext/`,
  `acp_adapter/`, `acp_registry/`, `eval/`, `optional-skills/`,
  `tui_gateway/`, `ui-tui/`, `cron/`, `docker/`, `nix/`, `packaging/`.
- `release-notes-and-fork-policies` (strategy: `keep-turbo`) —
  `RELEASE_v*.md`, `CLAUDE.md`, `PROGRESS.md`, `PRD.md`, `GOAL_RESULT.md`,
  `PERFORMANCE_ROADMAP.md`, `CONTRIBUTING.md`, `SECURITY.md`,
  `hermes-already-has-routines.md`.

### Daily-sync resilience (`scripts/hermes_turbo_daily_update.py`)

- **Conflict recovery**: a merge conflict no longer aborts with lost
  state. The script commits the partial state to a dedicated
  `codex/hermes-turbo-daily-{date}-CONFLICT` branch, writes the file list
  to `~/.local/state/hermes-turbo-agent/hermes-sync/latest-conflicts.md`,
  and exits with code `2` (distinct from generic failure `1`).
- **Network retry**: `git clone`, `git fetch`, and `git push` are wrapped
  in `_retry_network()` with up to 4 attempts and exponential backoff
  (2s, 4s, 8s, 16s). Only transient markers (DNS, RST, EOF, 503/504,
  TLS) trigger retry; permanent errors (auth, ref missing) abort
  immediately.
- **Worktree cleanup**: failed runs now actually remove the worktree
  (used to silently ignore removal errors via `ignore_errors=True`).
  Cleanup is skipped for conflict runs so the resolved branch SHA can be
  inspected.

### CI gate: YAML ↔ JSON policy mirror

New `scripts/check_sync_policy_mirror.py` parses both policy files and
reports drift (version, rule names, strategy, paths, allow_empty_globs,
allow_missing_paths). The daily sync invokes this before refreshing
benchmarks; CI can call it standalone.

### Test coverage

`tests/test_hermes_turbo_daily_update.py` (21 tests, all green) covers:

- `_looks_transient` recognizes network markers and skips permanent
  errors.
- `_retry_network` returns first success, retries transient + sleeps,
  aborts on permanent error, gives up after max attempts.
- `_merge_upstream` clean path and conflict snapshot (WIP branch,
  conflict report, ConflictError carries metadata).
- `_assert_hermes_turbo_personality` passes on the real repo and raises
  with `HERMES_TURBO_HOME` mention when markers are missing.
- `_write_report` emits both JSON and Markdown, including an error block
  when the run failed.

## Validation

```bash
# Smoke
python3 -c "from hermes_constants import HERMES_TURBO_HOME_ENV, display_hermes_home; print(HERMES_TURBO_HOME_ENV, display_hermes_home())"
# -> HERMES_TURBO_HOME ~/.hermes-turbo

# Tests (sync system + rebrand-sensitive)
python3 -m pytest tests/test_hermes_turbo_daily_update.py \
                  tests/test_refresh_sync_benchmarks.py \
                  tests/test_hermes_constants.py \
                  tests/test_hermes_home_profile_warning.py \
                  tests/test_hermes_turbo_brand_pass.py \
                  tests/test_hermes_turbo_home_bootstrap.py \
                  tests/test_auto_mapper.py \
                  tests/test_map_project_skill.py \
                  tests/hermes_cli/test_config.py -o addopts=
# -> 195 passed, 1 skipped

# Policy
python3 scripts/validate_sync_policy.py        # ok
python3 scripts/check_sync_policy_mirror.py    # ok

# No surviving Tota references in active code
git ls-files | xargs grep -lE "(\bTota\b|TOTA_|\btota_|\btota-|~/\.tota|/tota/|/tota_)"
# -> hermes_turbo_agent_benchmark_report.pdf (binary, expected)
```
