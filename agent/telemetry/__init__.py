"""Telemetry helpers for Hermes Turbo Agent.

Surfaces (all stdlib-only, no secrets):

- ``receipts`` — content-addressable append-only ledger (P7) + the
  deterministic ``content_hash`` primitive.
- ``token_savings`` — JSONL ledger of compression savings events; the
  data layer behind ``hermes report savings`` (#138).
- ``gain_analytics`` — aggregation/trends over the token-savings ledger.
- ``stage_timer`` / ``dashboard`` — per-stage timing ledger + percentile
  summaries surfaced by the ``/perf`` web view (#137).
- ``savings_report`` — weekly token-savings report with USD valuation.

Note: an earlier "keep only benchmark winners" cleanup removed the four
token-economy modules above while leaving their shipped #136-#139
consumers (and tests) in place, which hard-broke ``hermes report
savings``. They are intentionally retained here per the upstream-sync
``token-economy-and-telemetry-optimizations`` keep-turbo rule.
"""

from agent.telemetry.receipts import (
    Cost,
    Receipt,
    content_hash,
    default_receipts_dir,
    lookup_receipt,
    receipt_path,
    record_receipt,
)

__all__ = [
    "Cost",
    "Receipt",
    "content_hash",
    "default_receipts_dir",
    "lookup_receipt",
    "receipt_path",
    "record_receipt",
]
