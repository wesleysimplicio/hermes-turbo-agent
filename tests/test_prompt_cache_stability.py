"""Guard the prompt-cache stable prefix policy (ADR-0005).

Issue #80.  The system prompt is assembled from three tiers
(`stable` / `context` / `volatile`) by
``AIAgent._build_system_prompt_parts``.  The `stable` tier must be
byte-identical across two agents constructed with the same stable
inputs — otherwise upstream provider prefix caches (Anthropic,
OpenAI, OpenRouter, Cerebras, ...) miss on every turn and we pay full
token price for tens of thousands of tokens of system prompt.

If this test fails, someone added a non-deterministic value
(timestamp, session id, runtime status, etc.) into the `stable` tier.
Move it to `volatile_parts` instead — see ADR-0005.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


def _make_tool_defs(*names: str) -> list:
    """Minimal tool definition list accepted by AIAgent.__init__."""
    return [
        {
            "type": "function",
            "function": {
                "name": n,
                "description": f"{n} tool",
                "parameters": {"type": "object", "properties": {}},
            },
        }
        for n in names
    ]


def _build_agent():
    """Construct an AIAgent with the OpenAI client + tool loading mocked.

    Mirrors the fixture pattern from tests/run_agent/test_run_agent.py.
    """
    from run_agent import AIAgent

    with (
        patch("run_agent.get_tool_definitions", return_value=_make_tool_defs("web_search")),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        agent = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        agent.client = MagicMock()
    return agent


def test_stable_prefix_is_byte_identical_across_constructions():
    """Two agents with identical stable inputs must produce identical `stable`.

    This is the core ADR-0005 contract.  If this fails, the system
    prompt has acquired a non-deterministic value (timestamp, uuid,
    live-fs read, etc.) in the stable tier.
    """
    agent_a = _build_agent()
    agent_b = _build_agent()

    parts_a = agent_a._build_system_prompt_parts()
    parts_b = agent_b._build_system_prompt_parts()

    assert parts_a["stable"] == parts_b["stable"], (
        "Stable prefix diverged between two equivalent agent constructions. "
        "Something non-deterministic snuck into `stable_parts` — move it to "
        "`volatile_parts` (see docs/adr/0005-prompt-cache-stable-prefix.md)."
    )


def test_volatile_tier_contains_timestamp():
    """Sanity check: timestamps live in `volatile`, not `stable`.

    Confirms the test above is testing the right thing — if the
    timestamp ever moves up into `stable`, this assertion will keep
    pointing at the right tier and the byte-identity test will start
    failing.
    """
    agent = _build_agent()
    parts = agent._build_system_prompt_parts()
    assert "Conversation started:" in parts["volatile"], (
        "Expected the timestamp line in the volatile tier. "
        "If you moved it, update ADR-0005 and this test together."
    )
    assert "Conversation started:" not in parts["stable"], (
        "Timestamp leaked into the stable tier. This invalidates the "
        "prompt-cache prefix on every turn. See ADR-0005."
    )


def test_stable_prefix_does_not_contain_session_id():
    """Session ids belong in `volatile`, never in `stable`."""
    agent = _build_agent()
    agent.session_id = "session-deterministic-id-for-test"
    agent.pass_session_id = True
    parts = agent._build_system_prompt_parts()
    assert agent.session_id not in parts["stable"], (
        "Session id leaked into the stable prefix. Move it to volatile_parts."
    )


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-v"])
