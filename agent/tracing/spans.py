"""Stdlib-only OTel-compatible span emitter.

Records spans as dicts that can be drained into an OTLP exporter (or just
dumped to JSONL) without pulling the ~30 MB ``opentelemetry-sdk`` in. The
schema mirrors the OTel Span model: trace_id, span_id, parent_span_id,
name, start_ns, end_ns, attributes, status.

Use::

    from agent.tracing import span

    with span("router.decide", attributes={"text": "hi"}) as s:
        s.set_attribute("matched", True)

The recorder is process-global by default; ``set_default_recorder`` swaps
it (handy for tests + multi-process workers).
"""

from __future__ import annotations

import contextvars
import os
import secrets
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional


class SpanStatus(str, Enum):
    UNSET = "UNSET"
    OK = "OK"
    ERROR = "ERROR"


def _new_trace_id() -> str:
    return secrets.token_hex(16)  # 128-bit


def _new_span_id() -> str:
    return secrets.token_hex(8)  # 64-bit


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_ns: int = 0
    end_ns: int = 0
    attributes: Dict[str, Any] = field(default_factory=dict)
    status: SpanStatus = SpanStatus.UNSET
    error_message: Optional[str] = None

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    @property
    def elapsed_us(self) -> float:
        if not self.end_ns or not self.start_ns:
            return 0.0
        return (self.end_ns - self.start_ns) / 1_000.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "elapsed_us": round(self.elapsed_us, 3),
            "status": self.status.value,
            "error_message": self.error_message,
            "attributes": dict(self.attributes),
        }


@dataclass
class SpanRecorder:
    """In-memory span store. Thread-safe. Optionally writes to JSONL."""

    spans: List[Span] = field(default_factory=list)
    jsonl_path: Optional[str] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def emit(self, span_obj: Span) -> None:
        with self._lock:
            self.spans.append(span_obj)
            if self.jsonl_path:
                import json
                try:
                    with open(self.jsonl_path, "a", encoding="utf-8") as fh:
                        fh.write(
                            json.dumps(span_obj.to_dict(), separators=(",", ":"))
                            + "\n",
                        )
                except OSError:
                    pass

    def snapshot(self) -> List[Span]:
        with self._lock:
            return list(self.spans)

    def clear(self) -> None:
        with self._lock:
            self.spans.clear()


_default_recorder = SpanRecorder()
_current_span: contextvars.ContextVar[Optional[Span]] = contextvars.ContextVar(
    "hermes_current_span", default=None,
)


def current_recorder() -> SpanRecorder:
    return _default_recorder


def set_default_recorder(recorder: SpanRecorder) -> None:
    global _default_recorder
    _default_recorder = recorder


@contextmanager
def span(
    name: str,
    *,
    attributes: Optional[Dict[str, Any]] = None,
    recorder: Optional[SpanRecorder] = None,
) -> Iterator[Span]:
    """Context manager that records one span.

    The current-span contextvar establishes parent/child relationships
    automatically (works across asyncio tasks because of contextvars).
    Hot path: when ``attributes`` is None we reuse a shared empty dict so
    spans with no extra attrs do not allocate.
    """

    rec = recorder or _default_recorder
    parent = _current_span.get()
    new_span = Span(
        name=name,
        trace_id=parent.trace_id if parent else _new_trace_id(),
        span_id=_new_span_id(),
        parent_span_id=parent.span_id if parent else None,
        attributes=attributes if attributes is not None else {},
        start_ns=time.perf_counter_ns(),
    )
    token = _current_span.set(new_span)
    try:
        yield new_span
        if new_span.status == SpanStatus.UNSET:
            new_span.status = SpanStatus.OK
    except BaseException as exc:
        new_span.status = SpanStatus.ERROR
        new_span.error_message = repr(exc)
        raise
    finally:
        new_span.end_ns = time.perf_counter_ns()
        _current_span.reset(token)
        rec.emit(new_span)
