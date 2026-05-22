"""Deterministic no-LLM router for trivial runtime intents.

Maps short utterances to a precomputed answer or a tool-call dict via an
ordered list of regex rules. Stdlib-only.
"""
from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass, field
from typing import Callable, Iterable, List, Optional

Handler = Callable[[str, "re.Match[str]"], object]


@dataclass(frozen=True)
class RouteDecision:
    intent: str
    answer: Optional[str] = None
    tool_call: Optional[dict] = None
    confident: bool = True

    @property
    def is_match(self) -> bool:
        return self.answer is not None or self.tool_call is not None


@dataclass(frozen=True)
class RouteRule:
    intent: str
    pattern: "re.Pattern[str]"
    handler: Handler
    description: str = ""

    @classmethod
    def from_regex(cls, intent: str, regex: str, handler: Handler, description: str = "") -> "RouteRule":
        return cls(intent, re.compile(regex, re.IGNORECASE), handler, description)


@dataclass
class DeterministicRouter:
    rules: List[RouteRule] = field(default_factory=list)

    def add_rule(self, rule: RouteRule) -> None:
        self.rules.append(rule)

    def extend(self, rules: Iterable[RouteRule]) -> None:
        self.rules.extend(rules)

    def route(self, text: str) -> RouteDecision:
        if not isinstance(text, str):
            return RouteDecision(intent="unknown", confident=False)
        normalized = text.strip()
        if not normalized:
            return RouteDecision(intent="empty", confident=False)
        for rule in self.rules:
            m = rule.pattern.fullmatch(normalized) or rule.pattern.match(normalized)
            if not m:
                continue
            result = rule.handler(normalized, m)
            if isinstance(result, str):
                return RouteDecision(intent=rule.intent, answer=result)
            if isinstance(result, dict):
                return RouteDecision(intent=rule.intent, tool_call=result)
        return RouteDecision(intent="unknown", confident=False)


_HELP = (
    "Available trivial commands: help, date, time, ping, version, echo <text>, "
    "list files, pwd, whoami, clear, exit."
)

_RULES = (
    ("help", r"^(help|/help|\?|ajuda)$", lambda _t, _m: _HELP),
    ("date", r"^(show\s+date|what(?:'s|\s+is)\s+the\s+date|date|que\s+dia\s+(?:e|é)\s+hoje)\??$",
     lambda _t, _m: _dt.date.today().isoformat()),
    ("time", r"^(show\s+time|what(?:'s|\s+is)\s+the\s+time|time|que\s+horas\s+s(?:a|ã)o)\??$",
     lambda _t, _m: _dt.datetime.now().strftime("%H:%M:%S")),
    ("ping", r"^(ping|/ping)$", lambda _t, _m: "pong"),
    ("version", r"^(version|--version|-v|/version)$", lambda _t, _m: {"tool": "version", "args": {}}),
    ("echo", r"^echo\s+(?P<payload>.+)$", lambda _t, m: m.group("payload").strip()),
    ("list_files", r"^(list\s+files|ls|/ls|listar\s+arquivos)$",
     lambda _t, _m: {"tool": "list_files", "args": {"path": "."}}),
    ("pwd", r"^(pwd|where\s+am\s+i|current\s+directory)\??$",
     lambda _t, _m: {"tool": "pwd", "args": {}}),
    ("whoami", r"^(whoami|who\s+am\s+i)\??$", lambda _t, _m: {"tool": "whoami", "args": {}}),
    ("clear", r"^(clear|cls|/clear)$", lambda _t, _m: {"tool": "clear_screen", "args": {}}),
    ("exit", r"^(exit|quit|/exit|/quit|bye)$", lambda _t, _m: {"tool": "exit", "args": {}}),
)


def default_router() -> DeterministicRouter:
    """Return a router preloaded with the built-in rule set."""
    return DeterministicRouter(rules=[RouteRule.from_regex(i, r, h) for i, r, h in _RULES])
