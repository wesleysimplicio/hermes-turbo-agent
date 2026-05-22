# Upstream Sync Policy

This document explains the format of `/.upstream-sync-policy.yml` (root) and
how to keep it aligned with the JSON twin at
`docs/hermes-turbo-sync-policy.json`.

## Why two files

| File                                | Purpose                                                                     |
| ----------------------------------- | --------------------------------------------------------------------------- |
| `.upstream-sync-policy.yml` (root)  | Declarative, human-edited entry point. Easy to diff in PR reviews.          |
| `docs/hermes-turbo-sync-policy.json` | Machine twin consumed by `scripts/validate_sync_policy.py` and CI.          |

When a rule changes, edit the YAML first, then mirror it into the JSON.
A follow-up task may collapse the two by teaching the validator to read YAML
directly; until then the JSON is authoritative for tooling.

## Top-level fields

```yaml
version: 1                  # bump on incompatible schema change
updated_for_issue: 86       # GitHub issue that last touched the policy
owner: wesleysimplicio/...  # repo slug
update_process: []          # ordered list of human instructions
rules: []                   # ordered list of rule objects (see below)
```

## Rule object

```yaml
- name: short-kebab-id            # unique within file
  strategy: keep-turbo            # one of the five strategies below
  reason: >-                      # one to three sentences, present tense
    Why this rule exists.
  paths:                          # list of exact paths or glob patterns
    - some/file.py
    - some/dir/**
  allow_empty_globs: []           # optional: globs that may match nothing
  allow_missing_paths: []         # optional: exact paths that may not exist
```

## Strategies

| Strategy          | Behavior during sync                                                                 |
| ----------------- | ------------------------------------------------------------------------------------ |
| `keep-turbo`      | Fork wins. Upstream changes ignored unless this rule is rewritten.                   |
| `prefer-upstream` | Upstream wins. Use the narrowest other rule to carve out fork-owned exceptions.      |
| `merge`           | Combine upstream behavior on top of fork-owned surface (manual merge or 3-way tool). |
| `regenerate`      | Derived artifact. Rebuild from the source rule after sync (e.g. benchmark markdown). |
| `manual-review`   | No automation. A human compares fork vs upstream against latest runtime measurement. |

Pick the narrowest strategy that explains the file's ownership. Default to
`manual-review` when ownership is unclear.

## Path semantics

- Exact paths must exist in the working tree unless listed under
  `allow_missing_paths`.
- Glob patterns (`**`, `*`, `?`) must match at least one tracked file unless
  listed under `allow_empty_globs`.
- Rules are evaluated in order; the first matching rule wins for a given
  path. Put narrower rules above broader ones.

## How to update

1. Edit `/.upstream-sync-policy.yml` first. Add or modify rules.
2. Mirror the change into `docs/hermes-turbo-sync-policy.json` (same fields,
   same order).
3. Run `python scripts/validate_sync_policy.py` locally.
4. Validate YAML loads cleanly:
   `python3 -c 'import yaml; yaml.safe_load(open(".upstream-sync-policy.yml"))'`.
5. Commit both files together. Reference the issue or ADR in the commit body.

## When to add a new rule

- A new fork-owned directory or file appears (skill, profile, asset bundle).
- An upstream area becomes safe to default to `prefer-upstream` after enough
  proof.
- A `manual-review` rule has been observed stable for two sync cycles and can
  graduate to `merge`.

## Out of scope

- Secret material. The policy file ships in git; never reference unencrypted
  secrets here.
- One-shot migrations. Use an ADR plus a dated runbook, not a policy rule.
