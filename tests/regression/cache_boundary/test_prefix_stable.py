"""Regression: stable prompt prefix bytes survive repeated rendering.

Guards the contract from ADR-0005: the ``stable`` tier of the system
prompt must be byte-identical across turns and across sessions when
inputs match. If a future change inserts ``time.time()`` /
``uuid.uuid4()`` / hostname / cwd into the stable tier, this test
fires.

Strategy
--------
Provider-agnostic. Does not boot a full ``AIAgent`` (too heavy, too
many env knobs). Instead exercises the pure cache layer
(``apply_anthropic_cache_control``) on a fixed message tuple N times
and asserts every rendering is byte-identical to the first one.

Any non-determinism in the cache layer (set ordering, dict ordering,
leftover timestamp injection, etc.) trips this.

Refs #96, ADR-0005.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List

import pytest

from agent.prompt_caching import apply_anthropic_cache_control

# Representative stable prefix: system prompt + a few non-system turns.
# Inline to keep the test self-contained.
FIXED_MESSAGES: List[Dict[str, Any]] = [
    {
        "role": "system",
        "content": (
            "You are Hermes. Tools available: read_file, write_file, "
            "run_terminal. Identity stable across turns."
        ),
    },
    {"role": "user", "content": "list the repo"},
    {"role": "assistant", "content": "Running ls..."},
    {"role": "tool", "content": "README.md\npyproject.toml\n"},
    {"role": "user", "content": "open the readme"},
]

RUNS = 5


def _canonical(messages: List[Dict[str, Any]]) -> bytes:
    return json.dumps(messages, sort_keys=True, ensure_ascii=False).encode("utf-8")


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


@pytest.mark.parametrize("native_anthropic", [False, True])
@pytest.mark.parametrize("ttl", ["5m", "1h"])
def test_repeated_render_is_byte_identical(ttl: str, native_anthropic: bool) -> None:
    """N renderings of the same input must produce the same bytes."""
    digests: List[str] = []
    for _ in range(RUNS):
        out = apply_anthropic_cache_control(
            FIXED_MESSAGES,
            cache_ttl=ttl,
            native_anthropic=native_anthropic,
        )
        digests.append(_digest(_canonical(out)))

    unique = set(digests)
    assert len(unique) == 1, (
        f"cache layer is non-deterministic — got {len(unique)} distinct "
        f"renderings across {RUNS} runs (ttl={ttl}, native={native_anthropic}): "
        f"{digests}"
    )


def test_input_is_not_mutated() -> None:
    """A render must not edit the caller's list in place."""
    before = _digest(_canonical(FIXED_MESSAGES))
    apply_anthropic_cache_control(FIXED_MESSAGES, cache_ttl="5m")
    after = _digest(_canonical(FIXED_MESSAGES))
    assert before == after, "apply_anthropic_cache_control mutated the input list"


def test_empty_input_is_stable() -> None:
    """Edge case: empty input returns empty output, repeatedly."""
    for _ in range(RUNS):
        assert apply_anthropic_cache_control([], cache_ttl="5m") == []
