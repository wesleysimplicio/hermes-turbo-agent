"""Regression: cache_control breakpoints land at the expected positions.

Locks in the ``system_and_3`` layout from ``agent/prompt_caching.py``:
breakpoints belong on the system message + the last 3 non-system
messages. If a refactor drops one breakpoint or shifts it to an
earlier turn, the prompt-cache hit rate degrades silently in
production — this test catches it.

Refs #96, ADR-0005.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pytest

from agent.prompt_caching import apply_anthropic_cache_control


def _build(n_user_turns: int) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = [{"role": "system", "content": "S"}]
    for i in range(n_user_turns):
        msgs.append({"role": "user", "content": f"u{i}"})
        msgs.append({"role": "assistant", "content": f"a{i}"})
    return msgs


def _marker_indices(messages: List[Dict[str, Any]]) -> List[int]:
    """Return indices of messages carrying a cache_control marker."""
    out: List[int] = []
    for i, m in enumerate(messages):
        if m.get("cache_control"):
            out.append(i)
            continue
        content = m.get("content")
        if isinstance(content, list) and content:
            last = content[-1]
            if isinstance(last, dict) and last.get("cache_control"):
                out.append(i)
    return out


def test_breakpoint_on_system_message() -> None:
    rendered = apply_anthropic_cache_control(_build(4), cache_ttl="5m")
    assert 0 in _marker_indices(rendered), "no cache_control on system message"


def test_at_most_four_breakpoints() -> None:
    """Anthropic API caps cache_control at 4 markers per request."""
    rendered = apply_anthropic_cache_control(_build(10), cache_ttl="5m")
    assert len(_marker_indices(rendered)) <= 4


def test_breakpoints_target_tail_messages() -> None:
    """The 3 non-system breakpoints must hit the last 3 non-system msgs."""
    msgs = _build(5)  # 1 system + 10 non-system
    rendered = apply_anthropic_cache_control(msgs, cache_ttl="5m")
    indices = _marker_indices(rendered)
    # 4 total: system at 0, plus the last 3 of the conversation (8,9,10).
    assert indices == [0, 8, 9, 10], f"unexpected breakpoint layout: {indices}"


@pytest.mark.parametrize("ttl", ["5m", "1h"])
def test_ttl_is_propagated_to_marker(ttl: str) -> None:
    rendered = apply_anthropic_cache_control(_build(2), cache_ttl=ttl)
    system = rendered[0]
    content = system.get("content")
    if isinstance(content, list) and content:
        marker = content[-1].get("cache_control") or {}
    else:
        marker = system.get("cache_control") or {}
    assert marker.get("type") == "ephemeral"
    if ttl == "1h":
        assert marker.get("ttl") == "1h"
    else:
        # 5m is the default — Anthropic infers it from absence of `ttl`.
        assert "ttl" not in marker


def test_input_messages_are_never_mutated() -> None:
    """The caller's messages (and their content parts) must never be mutated.

    ``apply_anthropic_cache_control`` shallow-copies the list and deep-copies
    only the <=4 messages it marks (instead of deep-copying the whole
    transcript). This locks the contract that no cache_control ever leaks
    into the caller's own message objects.
    """
    msgs = _build(5)  # 1 system + 10 non-system
    ids_before = [id(m) for m in msgs]
    apply_anthropic_cache_control(msgs, cache_ttl="1h")
    for m in msgs:
        assert "cache_control" not in m
        content = m.get("content")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    assert "cache_control" not in part
    # Input list identity/membership preserved (function copied, not mutated).
    assert [id(m) for m in msgs] == ids_before


def test_untouched_messages_are_not_deep_copied() -> None:
    """Messages that get no breakpoint are shared by reference with output.

    Proves the optimization: only marked messages are copied; the long
    history tail is not cloned. Marked messages (system + last 3 non-system)
    are fresh copies; everything between is the same object.
    """
    msgs = _build(5)
    rendered = apply_anthropic_cache_control(msgs, cache_ttl="5m")
    assert rendered is not msgs
    assert rendered[0] is not msgs[0]      # system — marked -> copied
    assert rendered[-1] is not msgs[-1]    # last non-system — marked -> copied
    assert rendered[1] is msgs[1]          # untouched -> shared reference
    assert rendered[5] is msgs[5]          # untouched -> shared reference
