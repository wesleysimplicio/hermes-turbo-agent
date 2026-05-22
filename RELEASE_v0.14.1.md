# Tota Agent v0.14.1 — Security advisory for Sprint 4 hardening trio

**Release type:** Security advisory / patch release.
**Previous Tota version:** `0.14.0`.
**Issue:** `#55` — Cherry-pick upstream security trio.

This patch release lands the full Sprint 4 security trio requested in
issue `#55` and publishes it as a dedicated advisory release instead of
folding the changes back into the broader `0.14.0` sync notes.

## Included hardening

### 1. Sudo brute-force / stdin-fed escalation hardening

Already present on `main` before this patch release via the upstream
backports below:

- `9520a1cc` — block `sudo -S` password guessing when `SUDO_PASSWORD`
  is not set.
- `976d8e27` — classify stdin-fed / askpass / shell / list privilege
  sudo invocations as dangerous.

### 2. Dangerous-command detection bypass closures

Added in this release via upstream commit `6ba35ec3`:

- protect macOS `/private/{etc,var,tmp,home}` mirrors the same way as
  `/etc`, `/var`, `/tmp`, and `/home`
- catch `killall -9`, `-KILL`, `-SIGKILL`, `-s KILL`, and regex sweeps
- catch `find -execdir rm` alongside the older `find -exec rm` block

### 3. Tool-error sanitization before model reinjection

Added in this release via upstream commit `627f8a5f`:

- sanitize tool error strings before they re-enter model context
- strip structural framing tokens such as XML role tags, CDATA sections,
  and markdown code fences
- cap injected error bodies and wrap them with a stable
  `[TOOL_ERROR]` prefix

## Validation

Security regression suite:

```bash
.venv/bin/python -m pytest \
  tests/tools/test_approval.py \
  tests/tools/test_tirith_security.py \
  tests/tools/test_file_operations.py \
  tests/run_agent/test_tool_*.py \
  tests/test_sanitize_tool_error.py \
  -x
```

Result: `402 passed`.

Repo validation:

```bash
~/.local/bin/taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main
```

Result: `passed`.

Human checklist: `/Users/wesleysimplicio/.config/taskflow/reports/tota-agent-main-bde2378f/human-review.md`

## Advisory summary

Operators updating from `0.14.0` should treat `0.14.1` as the minimum
safe baseline for Sprint 4 work. The runtime now closes the known sudo
approval bypasses, command-detection gaps, and tool-error prompt
injection path tracked in issue `#55`.
