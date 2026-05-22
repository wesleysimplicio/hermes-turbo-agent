# Tota Agent v0.14.2 — Lazy-install advisory guard

**Release type:** Security / packaging patch release.
**Previous Tota version:** `0.14.1`.
**Issue:** `#41` — Adopt supply-chain advisory checker for installs.

This patch release closes the gap between the existing advisory surface
(`hermes doctor`, startup banner, gateway log warning) and the lazy-install
path introduced in the Hermes 0.14.0 sync. Tota now refuses to lazy-install
backend packages that are already known-bad and re-checks the installed
result before marking the feature usable.

## Included hardening

### 1. Pre-install advisory block in `tools/lazy_deps.py`

- candidate lazy-install specs are checked against
  `hermes_cli/security_advisories.py`
- if a feature pin matches a compromised version, `ensure()` aborts before
  invoking `uv` or `pip`
- the error points the operator at `hermes doctor` instead of suggesting a
  manual install of the poisoned package

### 2. Post-install advisory re-check

- after a successful lazy-install, Tota re-scans the installed packages that
  belong to the requested feature
- if the environment still resolves to an advisory-hit package version, the
  feature stays unavailable and the operator gets a clear remediation hint

### 3. Sprint backlog mirror update

- `docs/SPRINT_BACKLOG.md` now marks `#41` as done

## Validation

Targeted regression suite:

```bash
TMPDIR=/private/tmp/tota-agent-tmp \
HERMES_TEST_WORKERS=4 \
scripts/run_tests.sh \
  tests/tools/test_lazy_deps.py \
  tests/hermes_cli/test_security_advisories.py \
  tests/test_project_metadata.py \
  --tb=short \
  --basetemp=/private/tmp/tota-agent-pytest-0142
```

Lint / shell / diff checks:

```bash
.venv/bin/python -m ruff check \
  tools/lazy_deps.py \
  tests/tools/test_lazy_deps.py \
  tests/test_project_metadata.py
bash -n scripts/run_tests.sh
git diff --check
```

Repo validation:

```bash
~/.local/bin/taskflow run /Users/wesleysimplicio/Projetos/contribuicoes/hermes/tota-agent-main
```

## Operator summary

Operators updating from `0.14.1` should treat `0.14.2` as the minimum
baseline if they rely on lazy-installed backends. The advisory catalog now
protects both startup/runtime visibility and the install path itself.
