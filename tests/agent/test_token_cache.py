"""Tests for the incremental token-estimate cache (#83)."""

from __future__ import annotations

import pytest

from agent.context.token_cache import TokenEstimateCache, incremental_total


def _fake_tokenizer(text: str) -> int:
    """Deterministic stand-in: 1 token per 4 chars."""
    return max(1, (len(text) + 3) // 4)


class TestTokenEstimateCache:
    def test_miss_then_hit(self) -> None:
        c = TokenEstimateCache()
        v1 = c.estimate("hello world", model="m", tokenizer=_fake_tokenizer)
        v2 = c.estimate("hello world", model="m", tokenizer=_fake_tokenizer)
        assert v1 == v2
        s = c.stats()
        assert s.hits == 1
        assert s.misses == 1

    def test_different_models_do_not_share(self) -> None:
        c = TokenEstimateCache()
        c.estimate("hi", model="A", tokenizer=lambda _t: 999)
        v = c.estimate("hi", model="B", tokenizer=lambda _t: 1)
        assert v == 1

    def test_invalidate_model_drops_entries(self) -> None:
        c = TokenEstimateCache()
        c.estimate("a", model="m", tokenizer=_fake_tokenizer)
        c.estimate("b", model="m", tokenizer=_fake_tokenizer)
        c.estimate("a", model="other", tokenizer=_fake_tokenizer)
        removed = c.invalidate_model("m")
        assert removed == 2
        assert c.stats().size == 1

    def test_lru_evicts_oldest(self) -> None:
        c = TokenEstimateCache(max_entries=2)
        c.estimate("a", model="m", tokenizer=_fake_tokenizer)
        c.estimate("b", model="m", tokenizer=_fake_tokenizer)
        c.estimate("c", model="m", tokenizer=_fake_tokenizer)
        # 'a' should have been evicted.
        assert c.get("a", model="m") is None
        assert c.get("b", model="m") is not None
        assert c.get("c", model="m") is not None

    def test_incremental_total_uses_cache(self) -> None:
        c = TokenEstimateCache()
        calls = []

        def tok(text: str) -> int:
            calls.append(text)
            return _fake_tokenizer(text)

        segments = ["one", "two", "three", "one"]
        total = incremental_total(segments, model="m", tokenizer=tok, cache=c)
        assert total == sum(_fake_tokenizer(s) for s in segments)
        # "one" should have been tokenized only once.
        assert calls.count("one") == 1

    def test_negative_count_rejected(self) -> None:
        c = TokenEstimateCache()
        with pytest.raises(ValueError):
            c.put("x", -1, model="m")

    def test_zero_capacity_rejected(self) -> None:
        with pytest.raises(ValueError):
            TokenEstimateCache(max_entries=0)
