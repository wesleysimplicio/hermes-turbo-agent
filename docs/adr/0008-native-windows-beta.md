# ADR-0008: Native Windows beta integration test plan

**Status:** Proposed (Sprint 3 / issue #45).
**Date:** 2026-05-18.
**Owner:** TBD (needs Windows CI runner).

## Context

Hermes 0.14.0 shipped 40+ Windows-specific fixes alongside the
"native Windows (early beta)" support.  Those landed in our main via
the upstream merge (commit `ab61ec254`).  We need a Windows CI runner
to validate that:

1. Tota Agent boots on a fresh Windows 11 box without WSL.
2. The Rust `hermes_fast` extension builds (or gracefully skips) on
   Windows.
3. The smoke suite passes end-to-end.
4. No regression on the 40+ fixes (subprocess management, MinGit
   auto-install, MS Store python stub detection, npm prefix handling,
   ANSI sequence handling, file-locking semantics).

## What needs setting up

### 1. CI runner

Add `windows-latest` to the matrix in `.github/workflows/tests.yml`:

```yaml
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
```

### 2. Rust toolchain on Windows

The `hermes_fast` PyO3 extension needs the MSVC toolchain on
Windows.  Add `rustup-init.exe` to the Windows job's setup:

```yaml
- name: Install Rust toolchain (Windows)
  if: runner.os == 'Windows'
  run: |
    rustup default stable
    rustup target add x86_64-pc-windows-msvc
```

### 3. Smoke test

Tota-specific smoke test that proves the native-Windows path works:

```powershell
# tests/smoke/test_windows_smoke.ps1
tota --version
tota status
tota config show
tota tools list
tota skills list
```

### 4. Known Windows gotchas to test

- `Ctrl+C` in foreground mode (recent upstream fix).
- `Shift+Enter` for newline in chat.
- MinGit auto-install when system git is missing.
- MS Store python stub detection.
- npm prefix handling for `npx --yes @wesleysimplicio/llm-project-mapper`.
- Path normalisation in `$TOTA_HOME` (`C:\Users\...\.tota`).
- File-locking semantics in `hermes_state.py` (TOCTOU fix
  `7fee1f61e`).

## Output

- New job in `.github/workflows/tests.yml`.
- New `tests/smoke/test_windows_smoke.ps1` script.
- Documentation update in `docs/native-windows.md` (new file) listing
  known issues and workarounds.

## Acceptance criteria

- `windows-latest` job passes on every PR.
- Rust extension builds OR skips with a clear log message.
- Smoke test covers boot, status, config, tools list, skills list.

## Why this is open

A Windows CI runner pulls in additional GitHub Actions minutes
budget and an MSVC toolchain dependency.  The work itself is small
(one workflow change + one smoke script) but the operational
decision to add the runner is owner-level.

## References

- Hermes 0.14.0 RELEASE notes ("Windows — Native Support (Early
  Beta)" section).
- `tests/hermes_cli/test_gateway_wsl.py` (existing Windows-aware
  test).
- Issue #45.
