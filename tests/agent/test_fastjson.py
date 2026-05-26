from agent import _fastjson


def test_dumps_bytes_returns_bytes_and_round_trips():
    payload = {"b": [1, True], "a": "a\u00e7\u00e3o"}

    raw = _fastjson.dumps_bytes(payload, sort_keys=True)

    assert isinstance(raw, bytes)
    assert _fastjson.loads(raw) == payload
    assert _fastjson.dumps(payload, sort_keys=True) == raw.decode("utf-8")


def test_dumps_bytes_preserves_supported_json_options():
    payload = {"z": 1, "a": {"nested": True}}

    raw = _fastjson.dumps_bytes(payload, sort_keys=True, indent=2)

    assert isinstance(raw, bytes)
    assert b'\n  "a":' in raw
    assert _fastjson.loads(raw) == payload


def test_dumps_accepts_compact_separators():
    payload = {"b": 1, "a": 2}

    text = _fastjson.dumps(payload, sort_keys=True, separators=(",", ":"))
    raw = _fastjson.dumps_bytes(payload, sort_keys=True, separators=(",", ":"))

    assert text == '{"a":2,"b":1}'
    assert raw == b'{"a":2,"b":1}'
