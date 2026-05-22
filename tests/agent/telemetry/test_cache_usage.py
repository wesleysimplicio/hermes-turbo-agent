"""Tests for cache usage tracker (#96)."""

from __future__ import annotations

from agent.telemetry.cache_usage import (
    CacheUsage,
    CacheUsageTracker,
    extract_anthropic_usage,
    extract_cache_usage,
    extract_openai_usage,
)


class TestExtractAnthropic:
    def test_full_fields(self) -> None:
        resp = {
            "usage": {
                "input_tokens": 1000,
                "output_tokens": 200,
                "cache_creation_input_tokens": 500,
                "cache_read_input_tokens": 4000,
            }
        }
        u = extract_anthropic_usage(resp)
        assert u.cache_read_tokens == 4000
        assert u.cache_creation_tokens == 500
        assert u.input_tokens == 1000
        assert u.output_tokens == 200
        assert u.hit_rate > 0.7

    def test_missing_usage_returns_zeros(self) -> None:
        u = extract_anthropic_usage({})
        assert u.total_input == 0
        assert u.hit_rate == 0.0


class TestExtractOpenAI:
    def test_chat_completion_shape(self) -> None:
        resp = {
            "usage": {
                "prompt_tokens": 1000,
                "completion_tokens": 200,
                "prompt_tokens_details": {"cached_tokens": 750},
            }
        }
        u = extract_openai_usage(resp)
        assert u.cache_read_tokens == 750
        assert u.input_tokens == 250  # 1000 - 750
        assert u.output_tokens == 200

    def test_responses_api_shape(self) -> None:
        resp = {
            "usage": {
                "input_tokens": 800,
                "output_tokens": 100,
                "input_tokens_details": {"cached_tokens": 300},
            }
        }
        u = extract_openai_usage(resp)
        assert u.cache_read_tokens == 300
        assert u.input_tokens == 500


class TestDispatcher:
    def test_unsupported_provider_returns_none(self) -> None:
        assert extract_cache_usage("xai", {"usage": {}}) is None

    def test_anthropic_dispatch(self) -> None:
        u = extract_cache_usage("Anthropic", {"usage": {"cache_read_input_tokens": 5}})
        assert u is not None and u.provider == "anthropic"
        assert u.cache_read_tokens == 5


class TestTracker:
    def test_aggregate_two_responses(self) -> None:
        t = CacheUsageTracker()
        t.add(CacheUsage("anthropic", cache_read_tokens=100, input_tokens=50, output_tokens=10))
        t.add(CacheUsage("anthropic", cache_read_tokens=300, input_tokens=50, output_tokens=20))
        snap = t.snapshot()
        assert snap["samples"] == 2
        assert snap["cache_read_tokens"] == 400
        assert snap["by_provider"]["anthropic"] == 400
        assert snap["hit_rate"] > 0.7

    def test_zero_input_no_division_error(self) -> None:
        t = CacheUsageTracker()
        snap = t.snapshot()
        assert snap["hit_rate"] == 0.0
