"""Fastest-available JSON serde with graceful fallbacks.

Picks the fastest installed library at import time:

    1. ``msgspec`` — fastest for typed Struct decoding, smaller memory.
    2. ``orjson``  — fastest for plain dict/list dumps/loads.
    3. stdlib ``json`` — universal fallback.

Public surface stays minimal:

    dumps(obj)                  → bytes (always — orjson convention)
    loads(blob)                 → dict / list / scalar
    typed_decoder(struct_cls)   → callable[blob] → struct_cls instance
    has_msgspec(), has_orjson() → bool

Caller picks ``typed_decoder`` when they have a msgspec Struct; gets
sub-orjson decode-and-validate latency. The decoder gracefully degrades
to ``json.loads`` + manual instantiation when msgspec is absent.
"""

from __future__ import annotations

import json
from typing import Any, Callable, TypeVar

try:
    import msgspec  # type: ignore[import-not-found]
    _HAS_MSGSPEC = True
except ImportError:
    msgspec = None  # type: ignore[assignment]
    _HAS_MSGSPEC = False

try:
    import orjson  # type: ignore[import-not-found]
    _HAS_ORJSON = True
except ImportError:
    orjson = None  # type: ignore[assignment]
    _HAS_ORJSON = False


T = TypeVar("T")


class FastJSONUnavailable(RuntimeError):
    """Raised when a feature requires a backend that is not installed."""


def has_msgspec() -> bool:
    return _HAS_MSGSPEC


def has_orjson() -> bool:
    return _HAS_ORJSON


def dumps(obj: Any) -> bytes:
    """Serialise ``obj`` to JSON bytes, fastest backend first."""

    if _HAS_ORJSON:
        return orjson.dumps(obj)
    if _HAS_MSGSPEC:
        return msgspec.json.encode(obj)
    return json.dumps(obj, separators=(",", ":")).encode("utf-8")


def loads(blob: bytes | str) -> Any:
    """Deserialise ``blob`` into a plain Python object."""

    if isinstance(blob, str):
        if _HAS_ORJSON:
            return orjson.loads(blob.encode("utf-8"))
        if _HAS_MSGSPEC:
            return msgspec.json.decode(blob.encode("utf-8"))
        return json.loads(blob)
    if _HAS_ORJSON:
        return orjson.loads(blob)
    if _HAS_MSGSPEC:
        return msgspec.json.decode(blob)
    return json.loads(blob.decode("utf-8"))


def typed_decoder(struct_cls: type[T]) -> Callable[[bytes | str], T]:
    """Return a decoder that produces ``struct_cls`` instances.

    With msgspec installed, the decoder uses a ``msgspec.json.Decoder``
    which decodes-and-validates in a single pass — beats ``orjson`` +
    manual ``dataclass(**d)`` instantiation by ~3-5×. Without msgspec,
    decodes to dict and unpacks via ``**``.
    """

    if _HAS_MSGSPEC:
        decoder = msgspec.json.Decoder(struct_cls)

        def _decode_msgspec(blob: bytes | str) -> T:
            if isinstance(blob, str):
                blob = blob.encode("utf-8")
            return decoder.decode(blob)

        return _decode_msgspec

    # Fallback: try to instantiate via **. The caller is responsible for
    # types matching what the constructor accepts.
    def _decode_fallback(blob: bytes | str) -> T:
        data = loads(blob)
        if not isinstance(data, dict):
            raise FastJSONUnavailable(
                f"typed_decoder fallback expects a JSON object, got {type(data).__name__}",
            )
        return struct_cls(**data)  # type: ignore[call-arg]

    return _decode_fallback
