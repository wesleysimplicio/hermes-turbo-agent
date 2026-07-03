# Port Plan: run_agent.py — Upstream v0.17.0 Refactor

> **Issue:** [#180](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/180)
> **Status:** Planned
> **Upstream SHA:** `9be292f1e` (v0.17.0)
> **Merge commit:** `ff9e8c97e` (PR #179)
> **Last updated:** 2026-07-03

## Context

During PR #179 (upstream v0.17.0 merge), one conflict block spanned lines
13890–17793 of `run_agent.py` — approximately **3,900 lines** of fork code vs
~14 lines of upstream. To keep the fork's proven 16k-line agent loop working,
`run_agent.py` was resolved to **the fork version entirely**.

This document describes the structured, section-by-section plan to port the
upstream refactor onto the fork without regressing fork-owned optimizations.

## Why this is hard

| Factor | Detail |
|---|---|
| **File size** | `run_agent.py` is ~17k lines. The conflict region spans ~22% of the file. |
| **Perf patches (PR #178)** | Stream-diag byte proxy (`_diag["bytes"]` from delta lengths, not `len(repr(...))`) and tool-arg list-join (`O(n²)` → `O(n)`) are in this file. |
| **Fork hooks** | `agent/auto_mapper.py`, `agent/prompt_builder.py`, and delegation logic inject fork-specific behavior into the loop. |
| **Hot-path pass (3e68792ce)** | The 2026-07-01 hot-path pass lives partly in `run_agent.py` (stream diag). |
| **Tests** | ~20 test files under `tests/run_agent/` must pass after each section. |

## Strategy

### Approach: Manual section-by-section port (not `git am`)

Do **not** attempt to replay the upstream patch series directly — the conflict
is too large and the fork's file has diverged structurally. Instead:

1. Read the upstream `run_agent.py` at `9be292f1e` in full for the refactored
   region.
2. Understand *what* upstream changed structurally (not just line-level diff).
3. Manually re-apply each logical section, re-grafting fork customizations per
   section.
4. Run the focused test group for that section before moving to the next.

### Workspace

```bash
# Reference: upstream file at merge point
git show 9be292f1e:run_agent.py > /tmp/upstream-run_agent.py

# Reference: fork file at merge base (one parent before merge commit)
git show ff9e8c97e^1:run_agent.py > /tmp/fork-run_agent.py

# Reference: the actual conflict hunk
git diff ff9e8c97e^1 ff9e8c97e^2 -- run_agent.py > /tmp/merge-conflict-run_agent.diff

# Working file
run_agent.py  # in the working tree
```

## Section-by-section plan

### Section 1: Stream diagnostic byte proxy (fork-owned, keep)

**Upstream changes:** N/A (upstream does not have stream-diag).

**Files:** `run_agent.py`, `agent/chat_completion_helpers.py`

**Fork code to preserve:**

- `_diag["bytes"]` computed from delta text/reasoning/tool-arg lengths
  (not `len(repr(chunk/event))`). See `docs/hermes-100x-fast-reapply-playbook.md`
  Optimization Matrix row "stream diag byte proxy" at commit `3e68792ce`.

**Verification:** `tests/run_agent/test_stream_drop_logging.py`

**Action:** Ensure this section is not touched during the port. If upstream
touches adjacent code, isolate the fork's proxy in a helper function so the
surrounding refactor can proceed.

---

### Section 2: Tool-call arg accumulation (fork-owned, keep)

**Upstream changes:** N/A.

**Files:** `run_agent.py`, `agent/chat_completion_helpers.py`

**Fork code to preserve:**

- `entry["function"]["arguments"] += frag` → list append + single `"".join()`
  (eliminates `O(n²)` concatenation).

**Verification:** `tests/run_agent/test_streaming.py`,
`tests/run_agent/test_streaming_tool_call_repair.py`

**Action:** Same as Section 1 — isolate in helper.

---

### Section 3: Auto-mapper hook (fork-owned, keep)

**Files:** `run_agent.py`, `agent/auto_mapper.py`, `agent/prompt_builder.py`

**Fork code to preserve:**

- The `auto_mapper` call at session start (project mapping before first tool use).
- The `prompt_builder._build_system_prompt_parts` integration.

**Upstream v0.17.0 changes:** Upstream may have refactored the prompt builder
call site. Graft the fork's mapper hook onto the new prompt builder interface.

**Verification:** `tests/test_auto_mapper.py`, `tests/test_map_project_skill.py`

---

### Section 4: Parallel read-file guard and parsed-arg reuse (fork-owned)

**Files:** `run_agent.py`

**Fork code to preserve:**

- Parallel read-file scope guard.
- Parsed-arg reuse (avoids re-parsing tool arguments on parallel calls).

**Reference:** `dd09b3a43`

**Verification:**
`tests/run_agent/test_run_agent.py::TestConcurrentToolExecution`,
`tests/run_agent/test_run_agent.py::TestParallelScopePathNormalization`

---

### Section 5: Delegation config reuse and heartbeat fix (fork-owned)

**Files:** `run_agent.py`, `tools/delegate_tool.py`

**Fork code to preserve:**

- Delegation config reuse (avoid re-reading config on every delegate call).
- Heartbeat timeout fix for long-running subagents.

**Reference:** `dd09b3a43`, `4d5aba9d0`

**Verification:** `tests/tools/test_delegate.py`,
`tests/tools/test_delegate_subagent_timeout_diagnostic.py`

---

### Section 6: Batch session writes (fork-owned)

**Files:** `run_agent.py`, `hermes_state.py`

**Fork code to preserve:**

- Batch writes to session state (defer flush until batch threshold met).

**Reference:** `bfc1de9fc`, `4d5aba9d0`

**Verification:** `tests/test_hermes_state.py`,
`tests/run_agent/test_compression_persistence.py`

---

### Section 7: Main agent loop refactor (upstream structural change)

**This is the core of the port.** Upstream v0.17.0 may have restructured:

- The main `while` loop (event processing).
- Tool call dispatch / routing.
- Error handling and retry logic.
- Context management and message alternation enforcement.

**Approach:**

1. Read upstream's refactored loop logic.
2. Identify where fork hooks (auto-mapper, stream diag, delegation) need to
   be grafted onto the new structure.
3. Apply upstream's structural improvements (better error boundaries, cleaner
   dispatch, etc.) while layering fork customizations on top.

**Verification:** Full `tests/run_agent/` suite:
```
tests/run_agent/test_run_agent.py
tests/run_agent/test_stream_drop_logging.py
tests/run_agent/test_streaming.py
tests/run_agent/test_streaming_tool_call_repair.py
tests/run_agent/test_compression_persistence.py
tests/run_agent/test_tool_executor_contextvar_propagation.py
tests/run_agent/test_concurrent_interrupt.py
tests/run_agent/test_tool_call_guardrail_runtime.py
```

---

### Section 8: Final integration tests

After all sections are ported, run the full cross-cutting test suites:

```bash
# 1. Run all run_agent tests
python -m pytest tests/run_agent/ -q --tb=short

# 2. Regression: cache boundary
python -m pytest tests/regression/cache_boundary/ -q --tb=short

# 3. Think scrubber
python -m pytest tests/agent/test_think_scrubber.py -q --tb=short

# 4. Auto mapper
python -m pytest tests/test_auto_mapper.py tests/test_map_project_skill.py -q --tb=short

# 5. Delegation
python -m pytest tests/tools/test_delegate.py -q --tb=short

# 6. Full hermes_state
python -m pytest tests/test_hermes_state.py -q --tb=short

# 7. Compile check
python -m py_compile run_agent.py
```

## Perf patches checklist

After porting, verify each perf patch survived intact:

| Patch | File | Check |
|---|---|---|
| Stream diag byte proxy | `run_agent.py` | Assert `_diag["bytes"]` computed from delta lengths |
| Tool-arg list-join | `run_agent.py`, `agent/chat_completion_helpers.py` | No `+=` on string args |
| Prompt caching shallow copy | `agent/prompt_caching.py` | Only cache-marked messages deep-copied |
| Think scrubber precomputed tags | `agent/think_scrubber.py` | `_OPEN_TAGS_LOWER` / `_CLOSE_TAGS_LOWER` tuples |
| hermes_state fast json | `hermes_state.py` | `_json_loads` used in readers |

## Update sync-state.json

After the port is complete and merged, update
`scripts/upstream-sync/sync-state.json`:

```json
{
  "notes": "2026-07-01 full merge ... CAVEAT REMOVED: run_agent.py now ports upstream v0.17.0 refactor."
}
```

Remove the `CAVEAT` line and note the port was completed.

## Test coverage matrix

| Test file | Covers | Priority |
|---|---|---|
| `tests/run_agent/test_run_agent.py` | Main loop, tool execution, parallel guards | 🔴 Critical |
| `tests/run_agent/test_stream_drop_logging.py` | Stream diag byte proxy | 🔴 Critical |
| `tests/run_agent/test_streaming.py` | Streaming tool calls | 🔴 Critical |
| `tests/run_agent/test_streaming_tool_call_repair.py` | Tool arg accumulation | 🔴 Critical |
| `tests/run_agent/test_compression_persistence.py` | Batch session writes | 🟡 High |
| `tests/regression/cache_boundary/` | Prompt caching boundaries | 🟡 High |
| `tests/agent/test_think_scrubber.py` | Think scrubber perf | 🟡 High |
| `tests/test_auto_mapper.py` | Auto-mapper hook | 🟡 High |
| `tests/tools/test_delegate.py` | Delegation fixes | 🟢 Medium |
| `tests/test_hermes_state.py` | State management, batch writes | 🟢 Medium |

## Rollback plan

If a section port introduces regressions:

1. `git stash` the working changes.
2. `git checkout main -- run_agent.py` to restore the fork version.
3. Re-apply the problematic section with narrower scope.
4. Commit the corrected section and continue.

Each section should be committed separately so individual sections can be
reverted without losing progress on others.

---

*Documento mantido em: `docs/upstream-sync/run-agent-port-plan.md`*
*Issue de referência: [#180](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/180)*
*Última atualização: 2026-07-03*
