# ADR-0005: Prompt-cache stable prefix policy

**Status:** Accepted (codifies existing contract in `_build_system_prompt_parts`).
**Date:** 2026-05-19.
**Owner:** @wesleysimplicio.
**Related:** GitHub issue #80.

## Context

Modern provider APIs (Anthropic, OpenAI, OpenRouter, Cerebras, etc.)
charge less and respond faster when the **prefix bytes** of a prompt
match a previously-seen prefix.  Any divergence — even a single
character — invalidates the cache from that point onward.

If Hermes drops a timestamp, a session id, or a per-turn status string
into the **middle** of the system prompt, every subsequent token after
that string pays full price.  At Hermes' system-prompt size (tens of
thousands of tokens for skill-rich setups), this is a real money +
latency hit.

`run_agent.py::AIAgent._build_system_prompt_parts` already implements
the right shape: it returns three ordered tiers `stable` / `context` /
`volatile` and the caller joins them in that order.  This ADR makes the
contract explicit and adds a test guarding the stable prefix.

## Decision

The system prompt is assembled from three ordered tiers, joined with
`"\n\n"`:

### 1. `stable` (top — must be byte-identical across turns and across
   sessions when inputs match)

Allowed content:
- SOUL.md identity (or fallback `DEFAULT_AGENT_IDENTITY`).
- `HERMES_AGENT_HELP_GUIDANCE`.
- Tool-aware behavioural guidance keyed on `valid_tool_names`
  (memory, session_search, skills, kanban, computer_use, nous, etc.).
- Tool-use enforcement guidance + model-family operational guidance
  (Google, OpenAI, etc.) keyed on the *fixed* model string.
- Skills system prompt (skills metadata is stable per agent
  construction).
- Environment hints (WSL / Termux / etc.) — fixed per process.
- Platform hints — fixed per agent.

Forbidden content:
- Timestamps.
- Session ids.
- Per-turn runtime status (current cwd if it can change, current
  branch, last tool result, etc.).
- Anything that depends on `time.time()` or the live filesystem state
  past startup.

### 2. `context` (middle — stable per session, may vary between
   sessions)

Allowed content:
- Caller-supplied `system_message`.
- Context files discovered at cwd (`AGENTS.md`, `.cursorrules`,
  `CLAUDE.md`, etc.).

Notes:
- Context can legitimately change between two `hermes` invocations
  (different cwd, different `AGENTS.md`).  Within a single session,
  it must not change — that would invalidate the cache mid-session.

### 3. `volatile` (bottom — changes per turn, never expected to cache)

Required to live here:
- Memory snapshot blocks.
- USER.md profile block.
- External memory provider blocks.
- Timestamp line (`Conversation started: ...`).
- Session ID line.
- Live model / provider identity (mutable in some failover scenarios).

The volatile tier is at the **end** of the system prompt on purpose:
a divergence here only loses the last few hundred tokens of cache, not
the entire 30k-token prefix above it.

## Caching guarantees

* Two `AIAgent` instances constructed with the same model, provider,
  `valid_tool_names`, platform, and identity files must produce the
  same `stable` string.  Bytes-equal.  No exceptions.
* The full system prompt is cached on the agent instance
  (`_cached_system_prompt`) and never re-rendered mid-session, even
  when memory or user-profile content changes — that change applies
  the next turn through the standard message channel, not by editing
  the system prompt.

## How to extend safely

* New tool guidance → goes in the `stable` tier, gated on a fixed
  `valid_tool_names` check.
* New per-call status → goes in the `volatile` tier, **or** is
  attached as a user-message preamble for the turn.  Never inject into
  `stable` or `context`.
* New context source → goes in the `context` tier, must be deterministic
  given the cwd inputs.

## Test

`tests/test_prompt_cache_stability.py` exercises
`_build_system_prompt_parts` twice with the same stable inputs and
asserts the `stable` tier is byte-identical.  It also asserts the
`volatile` tier is permitted to differ across runs (sanity-check that
we're testing the right thing).

## Consequences

* New contributors get a documented rule instead of "ask Wesley".
* The test fails loudly the first time someone shoves a timestamp into
  `stable_parts`.
* The contract is enforced by code structure (three explicit tiers),
  not by review discipline alone.

## Non-goals

* This ADR does **not** add provider-side cache control directives
  (`cache_control: ephemeral`, OpenRouter `cache_breakpoints`, etc.).
  Those are tracked separately and orthogonal to prefix stability.
* This ADR does **not** redefine the message-list portion of the
  prompt (user / assistant / tool messages).  Cache control there is
  handled by the existing provider adapters.
