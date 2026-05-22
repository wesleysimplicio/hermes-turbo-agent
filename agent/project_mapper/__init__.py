"""Project fingerprint via manifest heuristics (P1).

Stdlib-only stack auto-detection. See ``agent/project_mapper/fingerprint.py``.
"""

from agent.project_mapper.fingerprint import (
    ProjectFingerprint,
    detect_fingerprint,
    fingerprint_to_dict,
)

__all__ = [
    "ProjectFingerprint",
    "detect_fingerprint",
    "fingerprint_to_dict",
]
