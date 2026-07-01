"""Fast JSON module — orjson primary, msgspec typed, stdlib fallback.

3-6x faster serialization than stdlib ``json`` using ``orjson``.
Graceful fallback when orjson is not installed.

Usage::

    from tools._fastjson import json

    data = json.loads(some_string)
    text = json.dumps(some_dict, indent=2)
    parsed = json.parse_tool_call(text)
"""

from typing import Any, Dict, Optional, Union

_has_orjson = False
_has_msgspec = False

try:
    import orjson as _orjson
    _has_orjson = True
except ImportError:
    _orjson = None

try:
    import msgspec
    _has_msgspec = True
except ImportError:
    msgspec = None


def _orjson_dumps(obj: Any, indent: Optional[int] = None, **kwargs) -> str:
    opt = 0
    if indent is not None:
        opt |= _orjson.OPT_INDENT_2
    try:
        opt |= _orjson.OPT_SORT_KEYS
    except AttributeError:
        pass
    opt |= _orjson.OPT_SERIALIZE_NUMPY
    raw = _orjson.dumps(obj, option=opt)
    return raw.decode("utf-8")


def _orjson_loads(s: Union[str, bytes]) -> Any:
    if isinstance(s, str):
        s = s.encode("utf-8")
    return _orjson.loads(s)


def _stdlib_dumps(obj: Any, **kwargs) -> str:
    import json as _json
    return _json.dumps(obj, **kwargs)


def _stdlib_loads(s: Union[str, bytes]) -> Any:
    import json as _json
    if isinstance(s, bytes):
        s = s.decode("utf-8")
    return _json.loads(s)


class _FastJsonModule:
    JSONDecodeError = (_orjson.JSONDecodeError if _has_orjson
                       else ValueError)

    def __init__(self):
        self._dumps = _orjson_dumps if _has_orjson else _stdlib_dumps
        self._loads = _orjson_loads if _has_orjson else _stdlib_loads
        self._has_orjson = _has_orjson
        self._has_msgspec = _has_msgspec

    @property
    def engine(self) -> str:
        return "orjson" if _has_orjson else "stdlib"

    def loads(self, s: Union[str, bytes]) -> Any:
        return self._loads(s)

    def dumps(self, obj: Any, **kwargs) -> str:
        return self._dumps(obj, **kwargs)

    def parse_tool_call(self, text: str) -> Dict[str, Any]:
        if _has_msgspec:
            return msgspec.json.decode(text.encode("utf-8"), type=dict)
        return self.loads(text)


json = _FastJsonModule()
__all__ = ["json"]
