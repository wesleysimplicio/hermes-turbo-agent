# Hermes Turbo Agent v0.15.0 — Rebranding + upstream sync hardening

**Release type:** Identity rename + sync-system hardening (minor bump for public-surface change).
**Previous version:** `0.14.2`.

This release closes two work streams: a complete rebrand of the fork to
**Hermes Turbo Agent**, and the follow-through on the audit gaps in the
daily upstream sync system that was introduced in 0.14.x (issues #85,
#86, #87).

## Identity rename

Every fork-native surface now consistently reads **Hermes Turbo Agent**:

- `pyproject.toml` description, console_scripts, version
- Python identifiers (`hermes_turbo_*` namespaces)
- Env vars (`HERMES_TURBO_HOME`, `HERMES_TURBO_AUTO_MAP`,
  `HERMES_TURBO_FAST_STATE`, `HERMES_TURBO_GATEWAY_SIDECAR`,
  `HERMES_TURBO_AGENT_*`)
- Paths (`.hermes-turbo/`, `~/.hermes-turbo`,
  `docs/assets/hermes-turbo-{brand,benchmark,social}/`,
  `hermes_turbo_agent_benchmark_report.pdf`, `hermes-turbo-agent.html`,
  `docs/hermes-turbo-{benchmark,identity-customization,social-storyboard}.md`,
  `scripts/{hermes_turbo_,install_hermes_turbo_,generate_hermes_turbo_,benchmark_hermes_turbo_}*`)
- Brand SVG aria-labels and inline benchmark caption text
- Release notes 0.13.x and 0.14.x were rewritten retroactively to use
  the canonical brand. Commit history is unchanged.

Console scripts:

| Script | Maps to |
|---|---|
| `hermes-turbo` | `hermes_cli.main:main` |
| `hermes-turbo-agent` | `run_agent:main` |
| `hermes-turbo-acp` | `acp_adapter.entry:main` |

The upstream `hermes` and `hermes-agent` aliases continue to work
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

# Tests
python3 -m pytest tests/test_hermes_turbo_daily_update.py \
                  tests/test_refresh_sync_benchmarks.py \
                  tests/test_hermes_constants.py \
                  tests/test_hermes_home_profile_warning.py \
                  tests/test_hermes_turbo_brand_pass.py \
                  tests/test_hermes_turbo_home_bootstrap.py \
                  tests/test_auto_mapper.py \
                  tests/test_map_project_skill.py \
                  tests/hermes_cli/test_config.py -o addopts=

# Policy
python3 scripts/validate_sync_policy.py
python3 scripts/check_sync_policy_mirror.py
```
