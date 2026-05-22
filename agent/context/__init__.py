"""Context utilities: incremental builder, token cache, and working-set retrieval.

Three coexisting subsystems:

- ``incremental`` (issue #83): ``IncrementalContextBuilder`` + ``ContextDelta``
  for append-only context construction that avoids re-walking the prefix.
- ``token_cache`` (issue #83): ``TokenEstimateCache`` with ``CacheStats`` and
  ``incremental_total`` — thread-safe, model-keyed token-count memoization
  integrated with the telemetry layer.
- ``working_set`` / ``retrieval`` (issue #92): ``WorkingSet`` with
  expand-on-demand retrieval (``ColdRef``, ``HotEntry``, ``RelevanceScorer``).
"""

from .incremental import ContextDelta, IncrementalContextBuilder
from .retrieval import RelevanceScorer, ScoredHandle
from .token_cache import CacheStats, TokenEstimateCache, incremental_total
from .working_set import ColdRef, HotEntry, WorkingSet, WorkingSetBudgetError

__all__ = [
    "ContextDelta",
    "IncrementalContextBuilder",
    "RelevanceScorer",
    "ScoredHandle",
    "CacheStats",
    "TokenEstimateCache",
    "incremental_total",
    "ColdRef",
    "HotEntry",
    "WorkingSet",
    "WorkingSetBudgetError",
]
