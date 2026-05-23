# ADR-0001: PyPI publishing strategy for Hermes Turbo Agent

**Status:** Draft (Sprint 3 / issue #39).
**Date:** 2026-05-18.
**Owner:** @wesleysimplicio.

## Context

Hermes Agent 0.14.0 ships as `pip install hermes-agent`. The Hermes Turbo fork
currently piggy-backs on that distribution name in `pyproject.toml`:

```toml
[project]
name = "hermes-agent"
version = "0.14.0"
```

To ship Hermes Turbo independently on PyPI we need to decide how to name and
version the wheel.

## Options

### A. Rename to `tota-agent` on PyPI

```toml
name = "tota-agent"
```

**Pros**
- Clean separation. Anyone running `pip install tota-agent` gets the fork.
- PyPI search surfaces the brand.

**Cons**
- Breaks anyone who has `hermes-agent` pinned in their requirements.
- The Python package directory `hermes_cli/` and the import path
  `from hermes_cli import ...` stay the same — confusing for newcomers.

**Effort** — Low. One line in `pyproject.toml`, plus a back-compat
metapackage if we want existing `pip install hermes-agent && hermes`
flows to keep working.

### B. Keep `hermes-agent`, ship `tota-agent` as a thin metapackage

```toml
# pyproject.toml stays at name = "hermes-agent"
# Additional packaging/tota-agent/pyproject.toml:
[project]
name = "tota-agent"
version = "0.14.0"
dependencies = ["hermes-agent==0.14.0"]
```

**Pros**
- Zero break for existing `hermes-agent` consumers.
- `pip install tota-agent` works for fork-discovery.
- One source tree, two PyPI listings, one source of truth.

**Cons**
- Two PyPI pages to maintain.
- `pip install tota-agent` pulls `hermes-agent` transitively — confusing
  for users who read `pip list` after installation.

**Effort** — Medium. Need a small extra `pyproject.toml` and a publishing
workflow that builds both.

### C. Dual-publish under both names with the same wheel content

Use `setuptools` to register the wheel under two distribution names. PyPI
doesn't natively support this — would require uploading the wheel twice
(once as `hermes-agent`, once as `tota-agent`), keeping versions in
lock-step.

**Pros**
- Same wheel, both names install the same thing.
- No metapackage indirection.

**Cons**
- PyPI gates name uniqueness; this is technically two separate uploads.
- High operational burden (sync versions, sync uploads, monitor both).
- Higher chance of drift between the two PyPI pages.

**Effort** — High. Custom upload tooling, dual release workflow.

## Decision

**Option B** — keep `hermes-agent` as the canonical wheel, publish
`tota-agent` as a thin metapackage that pins the same version.

**Rationale**
- Zero back-compat break — the upstream Hermes 0.14.0 PyPI rollout is
  recent, and any user who already wired `hermes-agent` into their
  requirements doesn't get disrupted.
- The Hermes Turbo brand still surfaces on PyPI via the metapackage page.
- The metapackage description can carry the Hermes Turbo tagline and link to the
  fork README; the underlying `hermes-agent` page stays neutral.
- Low ongoing maintenance — a single shared version number, one publish
  workflow that touches both.

## Consequences

- **`pip install tota-agent`** → installs `hermes-agent==X.Y.Z` →
  `hermes` and `tota` console scripts both available (the `tota` alias
  lands in this PR per Sprint 3 issue #46).
- **`pip list`** shows both packages, which may surprise newcomers.
  Documented in the README install section.
- The metapackage release lags by minutes after the canonical wheel
  uploads, but both share the same version so a "matching pair" is
  always available.

## Implementation plan (Sprint 3 follow-up)

1. Create `packaging/tota-agent/pyproject.toml` with the metapackage shell.
2. Add `scripts/publish_tota_metapackage.py` that:
   - Reads the version from the canonical `pyproject.toml`.
   - Builds the metapackage wheel and sdist.
   - Uploads both via `twine`.
3. Extend `.github/workflows/upload_to_pypi.yml` to publish the
   metapackage after the canonical upload succeeds.
4. Test on TestPyPI before the first production release.

## Rejected paths

- **Renaming the import path** `hermes_cli` → `tota_cli`: would break
  every existing plugin that imports `from hermes_cli import ...`. Issue
  #46 captures the lower-cost alternative (additional `tota`
  `console_scripts` alias).
- **Publishing under only `tota-agent`**: rejected for back-compat reasons
  above.

## References

- Issue #39 — PyPI publishing plan for Hermes Turbo Agent.
- Issue #46 — Decide `hermes_cli` → `tota_cli` rename + `console_scripts`
  plan.
- Upstream Hermes 0.14.0 PyPI rollout — `NousResearch/hermes-agent` PR
  #26593.
