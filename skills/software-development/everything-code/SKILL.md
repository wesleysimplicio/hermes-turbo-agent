---
name: everything-code
description: Apply ECC engineering patterns in Hermes.
version: 1.0.0
author: Affaan Mustafa (@affaan-m), adapted by Hermes Agent.
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    category: software-development
    tags: [engineering, context, evals, workflows, performance]
    related_skills:
      - autonomous-ai-agents/cavecrew
      - software-development/subagent-driven-development
      - software-development/test-driven-development
---

# Everything Code Skill

Everything Code is a Hermes adaptation of the useful, general-purpose parts of
Everything Claude Code: context budget discipline, eval-first engineering,
codebase onboarding, focused review loops, and cost-aware agent orchestration.

It does not import the full Everything Claude Code repository into context.
Instead, it keeps the default behavior small and points Hermes toward the
highest-leverage workflow habits.

## When to Use

Use this skill for software work where the agent should be faster and more
deliberate without losing verification discipline.

Good fits:

- onboarding into an unfamiliar repository
- planning implementation slices
- reducing context bloat
- deciding when to delegate work
- creating evals before a risky change
- optimizing agentic workflows
- reviewing AI-generated code for hidden risk

## Prerequisites

Expected Hermes capabilities:

- `search_files` for repository reconnaissance
- `read_file` for exact local context
- `patch` for scoped edits
- `terminal` for tests, benchmarks, and project commands
- `delegate_task` for independent subagent work

No ECC CLI, Claude Code plugin, MCP server, or hook installation is required.

## How to Run

Start with the smallest workflow that can prove progress.

For a new repo, perform quick onboarding:

- identify manifests, frameworks, entry points, tests, and build commands
- map top-level directories to purpose
- find the smallest representative user flow
- summarize conventions before editing

For implementation, use an eval-first loop:

- define done conditions
- capture baseline behavior when possible
- edit in small units
- run focused verification
- only broaden tests when the change touches shared behavior

## Quick Reference

Default decision rules:

- Use cheap checks before expensive model work.
- Prefer cached or previously read context over repeated broad scans.
- Delegate only independent work with a clear output contract.
- Keep long explanations out of subagent returns unless needed.
- Treat benchmarks as claims only after rerunning them.
- Preserve user changes and avoid unrelated refactors.

Context budget checklist:

```text
loaded context:
- repo instructions
- active skill text
- relevant files
- current diff
- latest test output

trim:
- stale investigation notes
- duplicate diagrams
- broad file dumps
- old benchmark claims
- unrelated docs
```

## Procedure

1. Define the user-visible outcome.
2. Find the smallest files that control that outcome.
3. Write a short plan only when the work has multiple moving parts.
4. Delegate investigation, bounded edits, or review when parallelism helps.
5. Keep implementation local when the next step is blocked on the result.
6. Run the narrowest useful verification.
7. Update docs and claims only after the behavior is validated.

## Pitfalls

- Do not preload a huge external skill pack into every session.
- Do not confuse a marketing number with a benchmark result.
- Do not let subagents rewrite files outside their assigned scope.
- Do not run full suites repeatedly when a focused check answers the question.
- Do not skip regression notes when changing agent behavior.

## Verification

For code changes, report:

- exact files changed
- tests or checks run
- failures that are unrelated or pre-existing
- residual risk
- follow-up benchmark command when performance is involved

Attribution: adapted from `affaan-m/everything-claude-code` concepts.
