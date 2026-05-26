"""Tests for ``agent.serde.fast_json`` (Proposta H)."""

from __future__ import annotations

import pytest

from agent.serde import dumps, has_msgspec, has_orjson, loads, typed_decoder


def test_dumps_returns_bytes() -> None:
    out = dumps({"a": 1, "b": "x"})
    assert isinstance(out, bytes)


def test_roundtrip_dict() -> None:
    payload = {"a": 1, "b": "x", "c": [1, 2, 3]}
    assert loads(dumps(payload)) == payload


def test_loads_accepts_str_and_bytes() -> None:
    assert loads(b'{"k":42}') == {"k": 42}
    assert loads('{"k":42}') == {"k": 42}


def test_loads_handles_lists_and_scalars() -> None:
    assert loads(b"[1, 2, 3]") == [1, 2, 3]
    assert loads(b"42") == 42
    assert loads(b"true") is True


def test_typed_decoder_with_dataclass_fallback() -> None:
    from dataclasses import dataclass

    @dataclass
    class Point:
        x: int
        y: int

    decode = typed_decoder(Point)
    p = decode(b'{"x": 3, "y": 4}')
    assert isinstance(p, Point)
    assert p.x == 3 and p.y == 4


def test_has_flags_are_booleans() -> None:
    assert isinstance(has_msgspec(), bool)
    assert isinstance(has_orjson(), bool)


def test_typed_decoder_with_msgspec_struct() -> None:
    msgspec = pytest.importorskip("msgspec")

    class Item(msgspec.Struct):
        sku: str
        qty: int

    decode = typed_decoder(Item)
    item = decode(b'{"sku":"A1","qty":3}')
    assert item.sku == "A1"
    assert item.qty == 3
