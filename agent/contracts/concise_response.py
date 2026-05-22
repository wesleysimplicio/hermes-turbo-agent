"""Concise response contracts (issue #101).

Reduces output-token usage by forcing the model into structured,
budget-capped responses. Each contract declares a `max_chars` budget;
any field that exceeds the budget is truncated by `enforce_budget`,
with a single trailing ellipsis to signal that truncation kicked in.

Contracts:
    * TerseAnswer  - short prose reply with optional citations.
    * ToolCall     - request to invoke a tool with named arguments.
    * Diagnostic   - structured error/warning/info signal.
    * TupleStatusEnvelope - opt-in bracketed runtime status (P4).

The intent is "narrow, predictable, cheap" - not a general DTO layer.
Validators run at construction time so contracts cannot escape the
process with over-budget strings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple

ELLIPSIS = "..."


class ConciseContractError(ValueError):
    """Raised when a contract is constructed with invalid input."""


def enforce_budget(value: str, max_chars: int) -> str:
    """Truncate `value` to at most `max_chars` chars, suffixing ELLIPSIS.

    Raises ConciseContractError when `max_chars` is smaller than the
    ellipsis length - we never want a budget that cannot signal
    truncation.
    """

    if max_chars < len(ELLIPSIS):
        raise ConciseContractError(
            f"max_chars={max_chars} is smaller than ellipsis length"
        )
    if not isinstance(value, str):
        raise ConciseContractError(f"expected str, got {type(value).__name__}")
    if len(value) <= max_chars:
        return value
    cutoff = max_chars - len(ELLIPSIS)
    return value[:cutoff] + ELLIPSIS


def _coerce_str(name: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ConciseContractError(f"{name} must be str, got {type(value).__name__}")
    return value


@dataclass
class TerseAnswer:
    """Short prose answer. Default budget tuned for chat replies."""

    MAX_CHARS: ClassVar[int] = 600
    MAX_CITATIONS: ClassVar[int] = 4
    MAX_CITATION_CHARS: ClassVar[int] = 120

    text: str
    citations: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.text = enforce_budget(_coerce_str("text", self.text), self.MAX_CHARS)
        if len(self.citations) > self.MAX_CITATIONS:
            self.citations = self.citations[: self.MAX_CITATIONS]
        self.citations = [
            enforce_budget(_coerce_str("citation", c), self.MAX_CITATION_CHARS)
            for c in self.citations
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {"text": self.text, "citations": list(self.citations)}


@dataclass
class ToolCall:
    """Structured tool invocation. Args are stringified key/value pairs."""

    MAX_NAME_CHARS: ClassVar[int] = 64
    MAX_ARGS: ClassVar[int] = 8
    MAX_ARG_KEY_CHARS: ClassVar[int] = 32
    MAX_ARG_VALUE_CHARS: ClassVar[int] = 240

    name: str
    args: List[Tuple[str, str]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.name = enforce_budget(_coerce_str("name", self.name), self.MAX_NAME_CHARS)
        if not self.name:
            raise ConciseContractError("tool name must be non-empty")
        if len(self.args) > self.MAX_ARGS:
            self.args = self.args[: self.MAX_ARGS]
        capped: List[Tuple[str, str]] = []
        for pair in self.args:
            if not (isinstance(pair, tuple) and len(pair) == 2):
                raise ConciseContractError("each arg must be a (key, value) tuple")
            key = enforce_budget(_coerce_str("arg key", pair[0]), self.MAX_ARG_KEY_CHARS)
            val = enforce_budget(
                _coerce_str("arg value", pair[1]), self.MAX_ARG_VALUE_CHARS
            )
            capped.append((key, val))
        self.args = capped

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "args": [list(a) for a in self.args]}


@dataclass
class Diagnostic:
    """Structured info / warning / error signal."""

    LEVELS: ClassVar[Tuple[str, ...]] = ("info", "warning", "error")
    MAX_CODE_CHARS: ClassVar[int] = 48
    MAX_MESSAGE_CHARS: ClassVar[int] = 280

    level: str
    code: str
    message: str

    def __post_init__(self) -> None:
        level = _coerce_str("level", self.level).lower()
        if level not in self.LEVELS:
            raise ConciseContractError(
                f"level must be one of {self.LEVELS}, got {self.level!r}"
            )
        self.level = level
        self.code = enforce_budget(_coerce_str("code", self.code), self.MAX_CODE_CHARS)
        if not self.code:
            raise ConciseContractError("code must be non-empty")
        self.message = enforce_budget(
            _coerce_str("message", self.message), self.MAX_MESSAGE_CHARS
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"level": self.level, "code": self.code, "message": self.message}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class TupleStatusEnvelope:
    """Opt-in bracketed runtime status (P4 / inspired by simplicio-prompt).

    Default = silent (zero output tokens). When ``HERMES_RUNTIME_STATUS=true``,
    ``render()`` emits the bracketed envelope. Per-field toggles override the
    master switch when explicitly set.

    Envs:
        HERMES_RUNTIME_STATUS              master switch (default: false)
        HERMES_RUNTIME_STATUS_SNAPSHOT     snapshot line  (default: master)
        HERMES_RUNTIME_STATUS_ACTIVE       active line    (default: master)
        HERMES_RUNTIME_STATUS_TOTAL        total line     (default: master)
        HERMES_RUNTIME_STATUS_NEXT         next-yool line (default: master)
        HERMES_RUNTIME_STATUS_PARTIAL      partial line   (default: master)
    """

    MAX_FIELD_CHARS: ClassVar[int] = 240

    snapshot: str = ""
    active: str = ""
    total: str = ""
    next_yool: str = ""
    partial: str = ""

    def __post_init__(self) -> None:
        self.snapshot = enforce_budget(
            _coerce_str("snapshot", self.snapshot), self.MAX_FIELD_CHARS
        )
        self.active = enforce_budget(
            _coerce_str("active", self.active), self.MAX_FIELD_CHARS
        )
        self.total = enforce_budget(
            _coerce_str("total", self.total), self.MAX_FIELD_CHARS
        )
        self.next_yool = enforce_budget(
            _coerce_str("next_yool", self.next_yool), self.MAX_FIELD_CHARS
        )
        self.partial = enforce_budget(
            _coerce_str("partial", self.partial), self.MAX_FIELD_CHARS
        )

    @staticmethod
    def is_enabled() -> bool:
        return _env_flag("HERMES_RUNTIME_STATUS", False)

    def render(self) -> Optional[str]:
        """Return the bracketed text, or ``None`` if the envelope is silent.

        Returns ``None`` (= emit no characters) when every per-field toggle
        evaluates to false. This is the design goal: zero output tokens by
        default.
        """

        master = self.is_enabled()
        toggles = {
            "snapshot": _env_flag("HERMES_RUNTIME_STATUS_SNAPSHOT", master),
            "active": _env_flag("HERMES_RUNTIME_STATUS_ACTIVE", master),
            "total": _env_flag("HERMES_RUNTIME_STATUS_TOTAL", master),
            "next": _env_flag("HERMES_RUNTIME_STATUS_NEXT", master),
            "partial": _env_flag("HERMES_RUNTIME_STATUS_PARTIAL", master),
        }
        if not any(toggles.values()):
            return None
        lines: List[str] = []
        if toggles["snapshot"]:
            lines.append(f"[Tuple Space Snapshot] {self.snapshot}".rstrip())
        if toggles["active"]:
            lines.append(f"[Active Agents/Subagents] {self.active}".rstrip())
        if toggles["total"]:
            lines.append(f"[Total Agents/Subagents] {self.total}".rstrip())
        if toggles["next"]:
            lines.append(f"[Próximo Yool a executar] {self.next_yool}".rstrip())
        if toggles["partial"]:
            lines.append(f"[Resultado parcial] {self.partial}".rstrip())
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot": self.snapshot,
            "active": self.active,
            "total": self.total,
            "next_yool": self.next_yool,
            "partial": self.partial,
        }
