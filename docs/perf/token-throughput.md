# Token throughput: incremental context and token cache

Tracking issue: [#83](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/83)

## Why this exists

Benchmarks show Hermes Turbo Agent matches or beats peers on most rows but
loses token-throughput to OpenClaw. Two low-risk wins close that gap:

1. Avoid re-sending the unchanged conversation prefix on every turn.
2. Avoid re-tokenizing content the agent already saw this session.

Both are pure local optimizations. No new dependency, stdlib only.

## Components

### `agent/context/incremental.py` — `IncrementalContextBuilder`

Tracks the last emitted prefix per `namespace` (recommended layout:
`{conversation_id}:{model}:{tokenizer_fingerprint}`) and yields a
`ContextDelta` containing only the new suffix when the prefix matches.

- Match path: `O(prefix_len)` hash of the prior prefix, then slice.
- Divergence path: full rebuild, no silent stale send. Triggered when the
  recorded prefix hash no longer matches (edit, branch, rollback) or when
  the namespace changes (model swap, tokenizer change).

Invalidation:

- `builder.reset(namespace)` — drop one conversation.
- `builder.reset()` — drop everything.
- Any divergence in serialized prefix bytes — automatic fallback.

### `agent/context/token_cache.py` — `TokenCache`

Bounded LRU mapping `(tokenizer_key, sha256(content)) -> token_count`.

- `cache.count(content, tokenizer_key, compute)` returns the cached count
  or runs `compute(content)`, stores, returns.
- `cache.invalidate()` clears everything;
  `cache.invalidate(tokenizer_key="deepseek-chat")` clears just that bucket.
- `cache.stats()` exposes `{size, maxsize, hits, misses, hit_rate}` for
  benchmarking and dashboards.

## Safety contract

- The token cache is keyed by `tokenizer_key`. Changing model or tokenizer
  fingerprint cannot return a stale count — different key, miss, recompute.
- The incremental builder verifies the recorded prefix hash against the new
  prefix on every call. A drift forces a full rebuild instead of a wrong
  delta.
- No I/O, no global state, no threading primitives required for read-mostly
  per-process usage. Wrap in a lock if you share across threads.

## Suggested integration

```python
from agent.context import IncrementalContextBuilder, TokenCache

builder = IncrementalContextBuilder()
cache = TokenCache(maxsize=4096)

def tokens_for(text: str, model: str) -> int:
    return cache.count(text, tokenizer_key=model, compute=real_tokenize)

delta = builder.build(
    namespace=f"{conversation_id}:{model}:{tokenizer_version}",
    messages=conversation,
)
if delta.is_full_rebuild:
    send_full(conversation)
else:
    send_appended(delta.new_messages)
```

## Benchmark plan

A focused micro-benchmark compares:

- Cold path: every turn re-tokenizes and re-serializes full context.
- Warm path: incremental delta + cached token counts.

Expected outcomes (to be confirmed on bench rig):

- Wall-clock per turn drops once the prefix stabilizes (turn 2+).
- Token-count math becomes a constant-time hashmap lookup.
- Memory bounded by `TokenCache.maxsize` + one prefix hash per namespace.
