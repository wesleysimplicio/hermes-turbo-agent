"""Regression tests for the deterministic, no-LLM router."""

from __future__ import annotations

import datetime as _dt
import re

import pytest

from agent.router.deterministic import (
    DeterministicRouter,
    RouteDecision,
    RouteRule,
    default_router,
)


@pytest.fixture()
def router() -> DeterministicRouter:
    return default_router()


@pytest.mark.parametrize(
    "utterance,expected_intent",
    [
        ("help", "help"),
        ("/help", "help"),
        ("ajuda", "help"),
        ("ping", "ping"),
        ("date", "date"),
        ("show date", "date"),
        ("what's the date", "date"),
        ("time", "time"),
        ("show time", "time"),
        ("list files", "list_files"),
        ("ls", "list_files"),
        ("pwd", "pwd"),
        ("whoami", "whoami"),
        ("who am i", "whoami"),
        ("clear", "clear"),
        ("exit", "exit"),
        ("quit", "exit"),
        ("version", "version"),
        ("echo hello world", "echo"),
    ],
)
def test_routes_trivial_intents(router: DeterministicRouter, utterance: str, expected_intent: str) -> None:
    decision = router.route(utterance)
    assert decision.is_match, f"expected match for {utterance!r}"
    assert decision.intent == expected_intent
    assert decision.confident is True


def test_answers_and_tool_calls(router: DeterministicRouter) -> None:
    assert router.route("ping").answer == "pong"
    assert "help" in router.route("help").answer.lower()
    assert router.route("echo   spaced   text  ").answer == "spaced   text"
    assert router.route("list files").tool_call == {"tool": "list_files", "args": {"path": "."}}
    assert router.route("--version").tool_call == {"tool": "version", "args": {}}
    assert router.route("date").answer == _dt.date.today().isoformat()
    assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", router.route("time").answer)


def test_unknown_intent_does_not_match(router: DeterministicRouter) -> None:
    decision = router.route("write me a sonnet about kafka rebalancing")
    assert decision.is_match is False
    assert decision.intent == "unknown"
    assert decision.confident is False


def test_empty_input(router: DeterministicRouter) -> None:
    assert router.route("").intent == "empty"
    assert router.route("    ").intent == "empty"


def test_non_string_input(router: DeterministicRouter) -> None:
    assert router.route(None).is_match is False  # type: ignore[arg-type]
    assert router.route(123).is_match is False  # type: ignore[arg-type]


def test_first_match_wins() -> None:
    calls = []

    def handler_a(_t: str, _m: "re.Match[str]") -> str:
        calls.append("a")
        return "A"

    def handler_b(_t: str, _m: "re.Match[str]") -> str:
        calls.append("b")
        return "B"

    router = DeterministicRouter()
    router.add_rule(RouteRule.from_regex("a", r"^foo$", handler_a))
    router.add_rule(RouteRule.from_regex("b", r"^foo$", handler_b))
    decision = router.route("foo")
    assert decision.answer == "A"
    assert calls == ["a"]


def test_route_decision_is_match_flag() -> None:
    assert RouteDecision(intent="x", answer="y").is_match is True
    assert RouteDecision(intent="x", tool_call={"tool": "y"}).is_match is True
    assert RouteDecision(intent="x").is_match is False
