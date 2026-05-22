# Hermes Agent v0.13.3 (v2026.5.17)

**Release Date:** May 17, 2026

> Tota Agent validation hardening for the canonical test runner, shutdown
> paths, auxiliary Codex timeouts, and ACP registry package metadata.

## Fixes

- Fixed `scripts/run_tests.sh` so the default no-argument invocation no longer
  fails under `set -u` on Bash with `ARGS[@]: unbound variable`.
- Disabled real macOS Keychain reads during the hermetic test runner while
  keeping the mocked Keychain tests active.
- Fixed Codex auxiliary timeout cleanup so both timer-driven and loop-detected
  timeouts close and evict the poisoned cached client wrapper.
- Fixed browser emergency cleanup so shutdown does not emit logging tracebacks
  when process-exit cleanup runs after test-runner streams are closed.
- Made shutdown forensics portable on macOS by falling back when GNU `timeout`
  is unavailable.
- Updated the ACP registry manifest version and `uvx` package pin to match the
  Python package version.
- Hardened environment-sensitive tests around Tota home paths, `/goal` state,
  gateway update restarts, WSL systemd detection, and optional platform tools.

## Validation

- `bash -n scripts/run_tests.sh`
- `.venv/bin/python -m pytest tests/acp/test_registry_manifest.py -q --tb=short --basetemp=.pytest-tmp-acp`
- `TMPDIR=/private/tmp/tota-agent-tmp HERMES_TEST_WORKERS=4 scripts/run_tests.sh --tb=short --basetemp=/private/tmp/tota-agent-pytest-main`
- `TMPDIR=/private/tmp/tota-agent-tmp HERMES_TEST_WORKERS=2 scripts/run_tests.sh tests/e2e tests/integration --tb=short --basetemp=/private/tmp/tota-agent-pytest-e2e-integration`
- `.venv/bin/python -m ruff check .`
- `.venv/bin/python scripts/check-windows-footguns.py --all`
- `taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main`
