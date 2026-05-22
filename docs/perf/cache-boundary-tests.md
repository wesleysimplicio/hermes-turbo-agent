# Prompt-cache boundary tests

Companion to ADR-0005 (`docs/adr/0005-prompt-cache-stable-prefix.md`)
and issue #96.

## What

Regression tests that guard the prompt-cache boundary:

- `tests/regression/cache_boundary/test_prefix_stable.py` — N renders
  of the same input produce byte-identical output. Catches stray
  `time.time()` / set ordering / dict ordering / hostname injection
  that would invalidate the cache prefix.
- `tests/regression/cache_boundary/test_cache_breakpoint_placement.py`
  — `cache_control` markers land on the system message plus the last
  three non-system messages (Anthropic caps at 4). Catches refactors
  that drop a breakpoint or slide it onto an earlier turn.
- `tests/regression/cache_boundary/live_check.sh` — opt-in live smoke
  against DeepSeek. Sends the same stable prefix twice and asserts
  the second call reports `prompt_cache_hit_tokens > 0`.

## Running

```bash
# Unit suite (default, no network)
python3 -m pytest tests/regression/cache_boundary/ -k "not live" -x

# Live smoke (requires real key)
HERMES_LIVE=1 DEEPSEEK_API_KEY=sk-... \
  tests/regression/cache_boundary/live_check.sh
```

## When to update

- New cache-control TTL or layout → extend
  `test_cache_breakpoint_placement.py` with the new expected indices.
- New stable-prefix input source → extend `FIXED_MESSAGES` in
  `test_prefix_stable.py` so the new bytes are covered.
- New provider with surfaced cache-hit telemetry (OpenAI / Anthropic
  cached input tokens, OpenRouter `cache_discount`) → add a parallel
  shell smoke alongside `live_check.sh`.
