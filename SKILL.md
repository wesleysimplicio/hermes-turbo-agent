---
name: hermes-turbo-agent
description: Use when installing Hermes Agent performance improvements.
version: 2.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, performance, installer, benchmarking, orjson, msgspec, uvloop, turbo]
    related_skills: [hermes-agent-skill-authoring, systematic-debugging]
---

# Hermes Turbo Agent

## Purpose

This is an executable installation and optimization procedure, not a passive recommendation list. When the user asks Hermes to read/install/apply this skill, begin the installation workflow immediately in the authorized Hermes project. Install optional acceleration packages, apply compatible structural changes, run tests and benchmarks, and report exactly what changed.

Never target a guessed repository. First identify the active Hermes checkout, profile, Python environment, branch, and working-tree state. Preserve existing uncommitted work.

## Installation workflow

Execute these steps in order when this skill is requested for installation or speed improvements:

1. Map the active project and Hermes checkout before editing.
2. Check `git status`, current branch, Python version, package manager, and active Hermes home.
3. Create a rollback point or worktree when the repository is clean. Never overwrite unrelated user changes.
4. Capture a baseline for cold start, warm start, tool discovery, session persistence, JSON/tool-call parsing, async throughput, and memory. Store results in a local report.
5. Detect platform and capabilities.
6. Install optional dependencies into the active Hermes environment, using the project's package manager:
   - `orjson`
   - `msgspec`
   - `uvloop` on supported Unix platforms only
   Keep Python `json` and `asyncio` fallbacks available.
7. Apply the smallest compatible code changes for the measured bottleneck:
   - use an internal fast-JSON adapter with `orjson` fallback;
   - use `msgspec` only for stable typed message/tool-call contracts;
   - enable `uvloop` only through capability detection;
   - batch session writes into one SQLite transaction per round;
   - cache tool discovery, schemas, and external metadata with versioning, TTL, atomic writes, and invalidation;
   - parallelize only independent operations with deterministic ordering, limits, timeouts, and cancellation.
8. Add or update regression tests and verify crash recovery, concurrency, invalid payloads, plugin/provider compatibility, and fallback paths.
9. Run the same benchmarks again in the same environment.
10. Keep a change only when functional tests pass and the measured path improves without a safety, compatibility, memory, or latency regression.
11. Produce a report containing installed packages, modified files, benchmark before/after, tests, fallback status, and rollback instructions.

## Required command patterns

Use the active project's package manager rather than guessing. Typical commands are:

```bash
python -m pip install orjson msgspec
# Unix/macOS/Linux only, when supported by the active Python environment:
python -m pip install uvloop
```

For a repository managed by `uv`, prefer:

```bash
uv add orjson msgspec
uv add --optional fast uvloop
```

For a repository managed by Poetry, use its dependency commands. Do not install into the system Python when a project virtual environment exists. If installation fails, retain the fallback path, document the failure, and continue only with safe changes.

## Implementation requirements

### `orjson`

Encapsulate JSON acceleration behind an internal adapter. Verify bytes versus strings, dates, exceptions, non-serializable objects, and all real payload shapes. Never replace the standard fallback without tests.

### `msgspec`

Use typed structs only where the contract is stable. Verify malformed payloads, optional fields, unknown fields, tool-call deltas, and compatibility with existing dictionaries and schemas.

### `uvloop`

Enable only on supported Unix platforms and only when importable. Keep `asyncio` as the default fallback on Windows, unsupported environments, and failures. Measure cold start, warm start, latency, and task throughput separately.

### Persistence, cache, and parallelism

Batch SQLite writes without changing message ordering or role alternation. Version and invalidate caches when Hermes, configuration, skills, plugins, providers, or schemas change. Use atomic writes and never cache secrets. Parallelize only independent operations and preserve deterministic result order.

## Non-negotiable invariants

- Keep the system prompt and prompt-cache prefix byte-stable for the life of a conversation.
- Never insert synthetic messages that break strict role alternation.
- Preserve Python and `asyncio` fallbacks.
- Put behavioral settings in `config.yaml`; keep secrets in `.env`.
- Do not add outbound telemetry without explicit opt-in.
- Do not discard user changes, force-push, delete branches, or rewrite history.
- Do not claim a benchmark gain that was not measured on the actual path.

## Acceptance criteria

- Baseline and post-change benchmarks are reproducible and comparable.
- `orjson`, `msgspec`, and `uvloop` installation status is verified.
- Unit and real-path E2E tests pass.
- Fallback paths are tested without optional dependencies.
- Configuration, plugins, skills, providers, security, prompt caching, and message alternation remain compatible.
- The diff is reviewable and rollback is documented.

## Version control

If the user explicitly requests publication, create a branch, commit the verified changes, push that branch, open a PR against the requested base, wait for checks, and merge only when the PR is mergeable. Never push directly to `main` when a PR is requested.
