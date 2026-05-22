# ADR-0003: Plan for cherry-picking the Hermes 0.14.0 security trio

**Status:** Accepted and landed in `v0.14.1` (Sprint 4 / issue #55).
**Date:** 2026-05-18.
**Owner:** @wesleysimplicio.

## Context

Hermes 0.14.0 closed three security categories that we want to pull
into Hermes Turbo:

1. **Sudo brute-force block** — upstream PR `NousResearch/hermes-agent#23736`.
   The approval gate now refuses `sudo -S` brute-force attempts and
   classifies stdin-fed / askpass-stripped sudo invocations as DANGEROUS.
2. **Dangerous-command bypass closures** — upstream PR `#26829`. Three
   known bypasses of dangerous-command detection are closed (inspired
   by Claude Code's command-detection work).
3. **Tool-error sanitization** — upstream PR `#26823`. Tool error
   strings are sanitised before being re-injected into the model
   context so a malicious file or remote service can't pass
   instructions to the agent through error output.

## Why these three first

Sprint 4's tracker (issue #25) names this trio as **land first**. The
rationale:

- All three close real attack surfaces with documented exploit paths.
- They predate other Sprint 4 features that will run on top of the
  hardened approval gate / error injection paths (`/handoff`, LSP
  diagnostics, OpenAI proxy).
- The diffs are small and contained — no plugin-system rework, no
  schema migrations.

## Plan

### Step 1 — Identify the upstream commits

For each PR, run:

```bash
git fetch upstream main --depth=2000
git log --grep='#23736' upstream/main --format='%H %s'
git log --grep='#26829' upstream/main --format='%H %s'
git log --grep='#26823' upstream/main --format='%H %s'
```

### Step 2 — Cherry-pick each onto a focused branch

One branch per upstream PR:

```bash
git checkout main && git pull origin main
git checkout -b security/sudo-bruteforce-block
git cherry-pick <sha-23736>
# resolve conflicts (expect: tools/approval.py, tools/file_operations.py)
# run pytest tests/tools/test_approval* tests/tools/test_tirith_security.py
git push -u origin security/sudo-bruteforce-block
```

Repeat for #26829 and #26823.

### Step 3 — Conflicts to expect

Files most likely to conflict because Hermes Turbo has customizations there:

| Upstream PR | File | Hermes Turbo customization |
| --- | --- | --- |
| #23736 | `tools/approval.py` | None expected. |
| #26829 | `tools/file_operations.py` | Hermes Turbo's hierarchical cache + streaming defaults. |
| #26823 | `tools/tool_result_classification.py` | Hermes Turbo's `agent/_fastjson.py` migration call sites. |

For each conflict, the rule is: keep Hermes Turbo's perf customizations, take
upstream's security logic. If the two are entangled, refactor so they
compose (e.g. extract the security check into a helper Hermes Turbo's perf path
calls).

### Step 4 — Tests

Each cherry-pick PR must run:

```bash
.venv/bin/python -m pytest \
    tests/tools/test_approval*.py \
    tests/tools/test_tirith_security.py \
    tests/tools/test_file_operations*.py \
    tests/run_agent/test_tool_*.py \
    -x
```

Plus add a regression test demonstrating the closed exploit (e.g. for
#23736: a test that fires 5 wrong sudo passwords in a row and asserts
the approval gate rate-limits).

### Step 5 — Land all three before any Sprint 4 features

Sprint 4 tracker (issue #25) explicitly lists this trio as the gating
work item. Cherry-pick PRs must be merged before #47–#54 PRs open.

### Step 6 — Hermes Turbo changelog + security advisory

Update `RELEASE_v0.14.0.md` (or open `RELEASE_v0.14.1.md` if the
manifest version bumps) to note the three closures and link to the
upstream PRs and CVE numbers (when assigned).

## Out of scope

The other 9 P0 / 50 P1 closures from Hermes 0.14.0 are NOT covered by
this ADR. Pull them via dedicated PRs only when an operator hits the
underlying issue — defaulting to "cherry-pick everything upstream
closed" is not realistic at our review budget.

## References

- Issue #25 — Sprint 4 tracker.
- Issue #55 — Security trio cherry-pick task.
- Upstream Hermes 0.14.0 RELEASE_v0.14.0.md (the "Security wave"
  section).
- Upstream PR `NousResearch/hermes-agent#23736`, `#26829`, `#26823`.
