# ADR-0002: `.github/workflows/lint.yml` fork-guard + `continue-on-error`

**Status:** Accepted (Sprint 1 / issue #32).
**Date:** 2026-05-18.
**Owner:** @wesleysimplicio.

## Context

PR #21's draft branch carried an unrelated `lint.yml` change discovered
by Copilot's review:

```yaml
# Before (origin/main)
- name: Post / update PR comment
  if: github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository
  continue-on-error: true
  uses: actions/github-script@60a0d83039c74a4aee543508d2ffcb1c3799cdea  # v7

# After (branch divergence)
- name: Post / update PR comment
  if: github.event_name == 'pull_request'
  uses: actions/github-script@3a2844b7e9c422d3c10d287c895573f7108da1b3  # v9
```

Three concrete problems with the divergence:

1. **Removed fork guard.** `GITHUB_TOKEN` is read-only on PRs from forks
   (no `issues: write`). The step would now run on fork PRs and fail
   with HTTP 403 on every `createComment`/`updateComment`.
2. **Removed `continue-on-error: true`.** Combined with the fork-guard
   removal, the whole job (and the required `lint-diff` check) would
   fail on every fork PR.
3. **Undocumented `github-script` v7 → v9 bump.** Should have landed in a
   focused PR with the changelog reviewed.

PR #21 restored `lint.yml` to `origin/main`'s state as a stop-gap. This
ADR is the long-term decision.

## Options

### A. Keep the guard + `continue-on-error` (status quo, current `main`)

Fork PRs simply skip the lint summary comment. No security risk, no
broken comment posts. This is what main has today.

### B. Switch the trigger to `pull_request_target`

Lets the comment step run with the base branch's `GITHUB_TOKEN`, which
DOES have `issues: write`. Allows fork PRs to receive the lint summary.

**Risk:** `pull_request_target` runs in the context of `main`'s
workflow, but with the PR's checkout. Misuse can lead to code-execution
vulnerabilities (a malicious fork PR could inject arbitrary commands
into the workflow). This is a well-known footgun.

To do it safely:
- Never `actions/checkout` the PR head with `pull_request_target`.
- Only run trusted code paths (e.g. read lint reports from artifacts
  uploaded by a separate `pull_request`-triggered job).
- Restrict the workflow permissions to the minimum needed.

### C. Use a separate trusted workflow for comment posting

Two-workflow split:
- `pull_request`-triggered workflow runs the linters, uploads results
  as an artifact, and posts NOTHING on fork PRs.
- `workflow_run`-triggered workflow (which runs in `main`'s context
  with the base token) downloads the artifact and posts the comment.

More code, more moving parts, but the security boundary is explicit.

### D. Move the bump to a dedicated PR

Independent of the comment-posting decision: the `github-script` v7 → v9
bump should land in its own PR with the changelog reviewed. Dependabot
already opened equivalent PRs upstream (NousResearch/hermes-agent#217902072,
#547835c5a, #589370a4c).

## Decision

**A (now) + D (next).**

- Keep the existing guard + `continue-on-error: true` for fork PRs.
  Posting a lint summary comment on fork PRs is not a P0 UX issue;
  reviewers can read the artifact directly. The complexity of B/C is
  not justified at the fork's current PR volume.
- Land the `github-script` action version bump in a dedicated PR via the
  same Dependabot flow upstream uses. Pin to a verified SHA; review the
  v7 → v9 changelog before merging.

## Consequences

- Fork PRs (rare at Hermes Turbo's current scale) don't get the inline lint
  summary comment. They still see ruff + ty results in the artifact
  uploaded by the workflow.
- Future request to surface the lint comment on fork PRs would
  re-evaluate option C (artifact-driven `workflow_run`).
- The version bump becomes a separate, reviewable change.

## References

- Copilot review on PR #21 — flagged the divergence.
- Issue #32 — tracks this decision.
- [GitHub Actions: `pull_request_target` event security
  considerations](https://docs.github.com/en/actions/security-guides/automatic-token-authentication#permissions-for-the-github_token).
