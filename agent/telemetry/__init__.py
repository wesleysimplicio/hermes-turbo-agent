"""Runtime performance telemetry for Hermes Turbo Agent.

Exposes lightweight stage timing primitives and a CLI dashboard reader.
No external dependencies; safe for production hot paths.
"""

from .stage_timer import StageTimer, record_stage, set_log_path, get_log_path

__all__ = ["StageTimer", "record_stage", "set_log_path", "get_log_path"]
