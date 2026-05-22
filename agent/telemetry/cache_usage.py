"""Provider prompt-cache usage tracker (issue #96).

Extracts ``usage.*`` fields from Anthropic and OpenAI responses, computes
hit-rate, and persists running totals. Anthropic exposes
``cache_creation_input_tokens`` + ``cache_read_input_tokens``; OpenAI
exposes ``prompt_tokens_details.cached_tokens``. We accept either shape
and never raise on a missing field — telemetry must be optional.

The tracker is in-memory; persistence is the caller's job (typically via
``telemetry.token_savings.record_token_saving``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional


def _int(d: Mapping[str, Any], key: str, default: int = 0) -> int:
    v = d.get(key, default)
    try:
        return int(v) if v is not None else default
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class CacheUsage:
    provider: str
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_input(self) -> int:
        return self.cache_read_tokens + self.cache_creation_tokens + self.input_tokens

    @property
    def hit_rate(self) -> float:
        denom = self.total_input
        return self.cache_read_tokens / denom if denom else 0.0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "hit_rate": round(self.hit_rate, 4),
        }


def extract_anthropic_usage(response: Mapping[str, Any]) -> CacheUsage:
    """Pull cache fields from an Anthropic ``Message`` response."""
    usage = response.get("usage") or {}
    return CacheUsage(
        provider="anthropic",
        cache_read_tokens=_int(usage, "cache_read_input_tokens"),
        cache_creation_tokens=_int(usage, "cache_creation_input_tokens"),
        input_tokens=_int(usage, "input_tokens"),
        output_tokens=_int(usage, "output_tokens"),
    )


def extract_openai_usage(response: Mapping[str, Any]) -> CacheUsage:
    """Pull cached_tokens from an OpenAI chat completion response.

    Handles both the chat-completions shape
    (``usage.prompt_tokens_details.cached_tokens``) and the responses-API
    shape (``usage.input_tokens_details.cached_tokens``).
    """
    usage = response.get("usage") or {}
    details = (
        usage.get("prompt_tokens_details")
        or usage.get("input_tokens_details")
        or {}
    )
    cached = _int(details, "cached_tokens")
    total_input = _int(usage, "prompt_tokens") or _int(usage, "input_tokens")
    return CacheUsage(
        provider="openai",
        cache_read_tokens=cached,
        cache_creation_tokens=0,
        input_tokens=max(0, total_input - cached),
        output_tokens=_int(usage, "completion_tokens") or _int(usage, "output_tokens"),
    )


def extract_cache_usage(provider: str, response: Mapping[str, Any]) -> Optional[CacheUsage]:
    """Dispatch on provider name. Returns ``None`` for unsupported providers."""
    p = (provider or "").lower()
    if p == "anthropic":
        return extract_anthropic_usage(response)
    if p in {"openai", "openai-chat", "openai-responses"}:
        return extract_openai_usage(response)
    return None


@dataclass
class CacheUsageTracker:
    """Aggregates usage across many responses for a single session."""

    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    samples: int = 0
    by_provider: Dict[str, int] = field(default_factory=dict)

    def add(self, usage: CacheUsage) -> None:
        self.cache_read_tokens += usage.cache_read_tokens
        self.cache_creation_tokens += usage.cache_creation_tokens
        self.input_tokens += usage.input_tokens
        self.output_tokens += usage.output_tokens
        self.samples += 1
        self.by_provider[usage.provider] = (
            self.by_provider.get(usage.provider, 0) + usage.cache_read_tokens
        )

    @property
    def total_input(self) -> int:
        return self.cache_read_tokens + self.cache_creation_tokens + self.input_tokens

    @property
    def hit_rate(self) -> float:
        denom = self.total_input
        return self.cache_read_tokens / denom if denom else 0.0

    def snapshot(self) -> Dict[str, Any]:
        return {
            "samples": self.samples,
            "cache_read_tokens": self.cache_read_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_input_tokens": self.total_input,
            "hit_rate": round(self.hit_rate, 4),
            "by_provider": dict(self.by_provider),
        }
