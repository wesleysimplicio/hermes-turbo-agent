# Upstream Hermes sync playbook

This playbook describes the capture/reapply system used to consume updates from
`NousResearch/hermes-agent` while preserving Hermes Turbo Agent customizations.

## Components

- `scripts/upstream-sync/capture-upstream.sh` clones (or fetches) upstream into
  a bare mirror under `.upstream-sync/upstream.git`, then writes the commit
  list and a patch series for every new commit since `last_sync_sha`.
- `scripts/upstream-sync/reapply.sh` checks out a dated sync branch from the
  current `HEAD`, runs `git am --3way` on the captured series, and logs
  conflicts and skipped patches without aborting the whole run.
- `scripts/upstream-sync/sync-state.json` is the persistent metadata file that
  tracks the last upstream SHA, branch, and run identifier. Capture reads it;
  operators (or future automation) update it after a successful merge.

## Standard run

```bash
# 1. Clean working tree.
git status

# 2. Capture upstream commits.
bash scripts/upstream-sync/capture-upstream.sh
# -> .upstream-sync/<RUN_ID>/{commits.txt,series.patch,manifest.json}

# 3. Dry-run to assess conflicts before touching local history.
bash scripts/upstream-sync/reapply.sh <RUN_ID> --dry-run

# 4. Apply the series onto a fresh branch.
bash scripts/upstream-sync/reapply.sh <RUN_ID> --base main
# -> branch upstream-sync/<RUN_ID>; conflicts captured in conflicts.txt.

# 5. Resolve conflicts, run lint/unit/e2e, then push and open a sync PR.

# 6. After merge, update scripts/upstream-sync/sync-state.json:
#    last_sync_sha   <- manifest.json:head_sha
#    last_sync_branch<- upstream-sync/<RUN_ID>
#    last_run_id     <- <RUN_ID>
#    last_sync_at    <- ISO 8601 UTC (e.g. 2026-05-21T12:34:56Z)
```

## Conflict policy

- Patches that touch paths owned by Hermes Turbo (see
  `docs/hermes-turbo-sync-policy.json`) are flagged in `conflicts.txt` for
  manual review.
- The reapply script aborts the `git am` session on conflict but leaves the
  branch checked out so the operator can cherry-pick or rewrite the patches.
- Re-run with `--dry-run` to confirm the series still applies after manual
  fixes upstream.

## Recovery

- The bare mirror at `.upstream-sync/upstream.git` is disposable; delete and
  let `capture-upstream.sh` recreate it if it gets corrupted.
- Each run is isolated under `.upstream-sync/<RUN_ID>/`, so older runs remain
  available for audit until pruned manually.
