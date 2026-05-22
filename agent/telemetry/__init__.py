"""Telemetry helpers for Hermes Turbo Agent.

Two coexisting subsystems:

- ``token_savings``: gain analytics for the token-economy budget (issues #81-#103).
- ``stage_timer``: lightweight runtime performance instrumentation for hot
  paths plus a CLI dashboard reader (issue #82).

Both are no-dependency and safe for production hot paths.
"""

from agent.telemetry.token_savings import (
    TokenSavingRecord,
    default_log_path,
    iter_records,
    record_token_saving,
)
from agent.telemetry.stage_timer import (
    StageTimer,
    record_stage,
    set_log_path,
    get_log_path,
)

__all__ = [
    "TokenSavingRecord",
    "default_log_path",
    "iter_records",
    "record_token_saving",
    "StageTimer",
    "record_stage",
    "set_log_path",
    "get_log_path",
]
