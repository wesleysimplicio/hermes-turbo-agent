"""Tests for ``agent.context`` working set + retrieval (Issue #92)."""

from __future__ import annotations

import pytest

from agent.context import ColdRef, RelevanceScorer, WorkingSet, WorkingSetBudgetError


def test_add_get_and_replace() -> None:
    ws = WorkingSet(token_budget=200)
    ws.add("task", "fix retrieval bug", kind="fact")
    e = ws.get("task")
    assert e is not None and e.content == "fix retrieval bug" and e.kind == "fact"
    ws.add("task", "y" * 80)
    assert len(ws) == 1


def test_lru_eviction_and_pin() -> None:
    ws = WorkingSet(token_budget=30)
    ws.add("a", "alpha" * 8)
    ws.add("b", "bravo" * 8)
    ws.touch("a")  # b is now LRU
    ws.add("c", "charlie" * 8)
    keys = ws.hot_keys()
    assert "b" not in keys and "a" in keys and "c" in keys
    ws.add("pinned", "p" * 16, pinned=True)
    ws.add("x1", "x" * 16)
    ws.add("x2", "z" * 16)
    assert "pinned" in ws


def test_budget_errors() -> None:
    ws = WorkingSet(token_budget=5)
    with pytest.raises(WorkingSetBudgetError):
        ws.add("too_big", "x" * 4000)
    ws2 = WorkingSet(token_budget=20)
    ws2.add("p1", "p" * 40, pinned=True)
    ws2.add("p2", "q" * 40, pinned=True)
    with pytest.raises(WorkingSetBudgetError):
        ws2.add("new", "n" * 40)
    with pytest.raises(ValueError):
        WorkingSet(token_budget=0)


def test_cold_ref_lazy_load_and_expand_collapse() -> None:
    loads = {"n": 0}

    def loader() -> str:
        loads["n"] += 1
        return "the full doc body for Foo class"

    ws = WorkingSet(token_budget=2000)
    ws.register_cold(ColdRef("doc", "snippet", "doc: defines Foo", loader,
                             source="repo/doc", tags=("py",)))
    summary = ws.get("doc")
    assert summary is not None and summary.kind == "summary" and loads["n"] == 0
    promoted = ws.expand("doc")
    assert "Foo class" in promoted.content and promoted.kind == "snippet"
    ws.collapse("doc")
    assert ws.get("doc").content == "doc: defines Foo"
    with pytest.raises(KeyError):
        ws.expand("ghost")


def test_large_inputs_stay_under_budget() -> None:
    """AC: large inputs cannot blow the configured token budget."""
    ws = WorkingSet(token_budget=500)
    for i in range(50):
        ws.register_cold(ColdRef(f"f{i}", "snippet", f"f{i} line",
                                 loader=lambda i=i: "PAYLOAD " * 5000))
    assert ws.tokens_used <= ws.token_budget
    with pytest.raises(WorkingSetBudgetError):
        ws.expand("f0")
    assert ws.tokens_used <= ws.token_budget


def test_remove_and_unpin() -> None:
    ws = WorkingSet(token_budget=200)
    ws.add("a", "x" * 80, pinned=True)
    ws.unpin("a")
    assert ws.remove("a") and ws.tokens_used == 0 and not ws.remove("a")


def test_relevance_scorer() -> None:
    scorer = RelevanceScorer({
        "auth": "login session token oauth jwt",
        "billing": "invoice stripe payment subscription",
        "ws": "context working set retrieval expand cold hot",
    })
    assert scorer.score("expand working set retrieval")[0].key == "ws"
    assert scorer.score("") == []
    assert scorer.best("") is None
    assert scorer.score("zzz nothing matches") == []
    best = RelevanceScorer.from_pairs([("a", "http client"), ("b", "db driver")]).best("http tuning")
    assert best is not None and best.key == "a" and best.score > 0


def test_end_to_end_pick_and_expand() -> None:
    summaries = {
        "auth.py": "module auth login session token",
        "ctx.py": "module context working set retrieval expand cold hot",
    }
    payloads = {"auth.py": "auth code", "ctx.py": "ctx code with WorkingSet"}
    ws = WorkingSet(token_budget=4000)
    for k, s in summaries.items():
        ws.register_cold(ColdRef(k, "snippet", s, loader=lambda k=k: payloads[k]))
    pick = RelevanceScorer(summaries).best("how does the working set expand cold refs")
    assert pick is not None and pick.key == "ctx.py"
    assert "WorkingSet" in ws.expand(pick.key).content
