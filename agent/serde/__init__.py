"""Fast serialisation primitives (Proposta H — leverage msgspec/orjson)."""

from agent.serde.fast_json import (
    FastJSONUnavailable,
    dumps,
    has_msgspec,
    has_orjson,
    loads,
    typed_decoder,
)

__all__ = [
    "FastJSONUnavailable",
    "dumps",
    "has_msgspec",
    "has_orjson",
    "loads",
    "typed_decoder",
]
