# Context working set with expand-on-demand retrieval

Tracks Issue [#92](https://github.com/wesleysimplicio/hermes-turbo-agent/issues/92).
Module: `agent/context/`.

## Shape

`WorkingSet` keeps a small **hot** LRU of `HotEntry` objects within a
token budget, plus a side-store of `ColdRef` handles whose payload loads
lazily. `HotEntry.kind` is `fact | snippet | signature | summary | diff
| log | evidence`. Registering a cold ref also writes its `summary` into
hot so the model knows the handle exists.

## API

```python
from agent.context import WorkingSet, ColdRef, RelevanceScorer

ws = WorkingSet(token_budget=4000)
ws.add("task", "fix retrieval bug", kind="fact", pinned=True)

ws.register_cold(ColdRef(
    key="agent/run_agent.py",
    kind="snippet",
    summary="run_agent.py: AIAgent orchestrator",
    loader=lambda: open("agent/run_agent.py").read(),
))

scorer = RelevanceScorer({k: ws.get(k).content for k in ws.cold_keys()})
pick = scorer.best("where is AIAgent constructed")
if pick:
    full = ws.expand(pick.key)   # promotes cold -> hot
    ws.collapse(pick.key)        # back to summary when done
```

## Budget + eviction

LRU over the hot `OrderedDict`. `pin(key)` makes an entry non-evictable.
If no unpinned entry can be evicted to fit a new one, `add` / `expand`
raises `WorkingSetBudgetError`.

## Retrieval

`RelevanceScorer` is a stdlib TF-IDF cosine ranker (no numpy / sklearn);
build once per task, call `best` or `score(top_k=N)`.

## Acceptance for Issue #92

Working-set model for facts/files/symbols/diffs/commands/evidence;
snippets+summaries by default with explicit `expand`/`collapse` API;
token-budget LRU with pin/unpin; test asserts large inputs stay under
budget; pure stdlib for every adapter.
