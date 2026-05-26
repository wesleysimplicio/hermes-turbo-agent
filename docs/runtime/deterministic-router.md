# Deterministic Router (issue #99)

## Why
Trivial runtime decisions — command classification, output routing, cache
invalidation, validation scope — collapse to regex/keyword rules. Sending
them to an LLM wastes tokens and adds latency.

## Modules
- `agent/router/deterministic.py` — ordered rule engine. `default_router()`
  ships rules for: `help`, `date`, `time`, `ping`, `version`, `echo`,
  `list_files`, `pwd`, `whoami`, `clear`, `exit`. Each rule maps an utterance
  to a string answer or a `{tool, args}` dict.
- `agent/router/fallback.py` — `RouterWithFallback` escalates unmatched
  utterances to an injected LLM callable. `RouterMetrics` exposes
  `deterministic_hits`, `llm_escalations`, `empty_or_invalid`, and
  `avoided_llm_calls`.

## Flow
1. `decide(text)` consults the deterministic router. Match -> count hit,
   return.
2. Empty / non-string / no LLM configured -> count empty_or_invalid, return
   unknown.
3. Otherwise escalate to the LLM callable and normalize the result.

## Adding a rule
```python
from agent.router import RouteRule, default_router

r = default_router()
r.add_rule(RouteRule.from_regex(
    "cache_clear", r"^(cache\s+clear|clear\s+cache)$",
    lambda _t, _m: {"tool": "cache_clear", "args": {}},
))
```
First match wins. Anchor patterns (`^...$`).

## AC mapping
- No-LLM classification: rules above.
- Token-saver / validation scope: rule handlers return tool calls; caller wires.
- Metrics for avoided calls: `RouterMetrics.avoided_llm_calls`.
- LLM fallback only when uncertain: `RouterWithFallback.decide`.
- Regression tests: `tests/router/test_deterministic.py`,
  `tests/router/test_fallback.py` (10+ trivial intents).
