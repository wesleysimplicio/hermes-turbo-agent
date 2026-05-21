"""Hot working set + cold ref store with LRU eviction and expand-on-demand.

Hermes keeps a small hot set of facts (snippets, signatures, summaries) and
parks large blobs (full files, diffs, logs) as cold refs. ``expand(handle)``
promotes a cold ref into hot on demand; LRU eviction (skipping pinned
entries) keeps the budget. Pure stdlib so it runs in every adapter.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional


class WorkingSetBudgetError(RuntimeError):
    """Raised when an entry cannot fit the configured token budget."""


def _tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


@dataclass
class HotEntry:
    key: str
    kind: str  # fact | snippet | signature | summary | diff | log | evidence
    content: str
    tokens: int
    pinned: bool = False
    source: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)


@dataclass
class ColdRef:
    """Handle to a large blob; ``loader`` is invoked lazily by ``expand``."""

    key: str
    kind: str
    summary: str
    loader: Callable[[], str]
    source: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)


class WorkingSet:
    """LRU-bounded hot set + cold ref side-store."""

    def __init__(self, token_budget: int = 4000,
                 token_estimator: Callable[[str], int] = _tokens) -> None:
        if token_budget <= 0:
            raise ValueError("token_budget must be positive")
        self._budget = token_budget
        self._estimate = token_estimator
        self._hot: "OrderedDict[str, HotEntry]" = OrderedDict()
        self._cold: dict[str, ColdRef] = {}
        self._used = 0

    @property
    def token_budget(self) -> int:
        return self._budget

    @property
    def tokens_used(self) -> int:
        return self._used

    def __len__(self) -> int:
        return len(self._hot)

    def __contains__(self, key: object) -> bool:
        return key in self._hot

    def __iter__(self) -> Iterator[HotEntry]:
        return iter(self._hot.values())

    def add(self, key: str, content: str, *, kind: str = "fact", pinned: bool = False,
            source: Optional[str] = None, tags: tuple[str, ...] = ()) -> HotEntry:
        tokens = self._estimate(content)
        if tokens > self._budget:
            raise WorkingSetBudgetError(
                f"entry {key!r} needs {tokens} > budget {self._budget}")
        if key in self._hot:
            self._used -= self._hot[key].tokens
            del self._hot[key]
        self._make_room(tokens)
        entry = HotEntry(key=key, kind=kind, content=content, tokens=tokens,
                         pinned=pinned, source=source, tags=tags)
        self._hot[key] = entry
        self._used += tokens
        return entry

    def get(self, key: str) -> Optional[HotEntry]:
        entry = self._hot.get(key)
        if entry is not None:
            self._hot.move_to_end(key)
        return entry

    def touch(self, key: str) -> None:
        if key in self._hot:
            self._hot.move_to_end(key)

    def pin(self, key: str) -> None:
        if key in self._hot:
            self._hot[key].pinned = True

    def unpin(self, key: str) -> None:
        if key in self._hot:
            self._hot[key].pinned = False

    def remove(self, key: str) -> bool:
        entry = self._hot.pop(key, None)
        if entry is None:
            return False
        self._used -= entry.tokens
        return True

    def hot_keys(self) -> list[str]:
        return list(self._hot.keys())

    def cold_keys(self) -> list[str]:
        return list(self._cold.keys())

    def register_cold(self, ref: ColdRef) -> None:
        """Register a cold handle and stash its summary in hot."""
        self._cold[ref.key] = ref
        self.add(ref.key, ref.summary, kind="summary",
                 source=ref.source, tags=ref.tags)

    def expand(self, key: str) -> HotEntry:
        """Materialise a cold ref into the hot set on demand."""
        ref = self._cold.get(key)
        if ref is None:
            raise KeyError(f"no cold ref for {key!r}")
        return self.add(key, ref.loader(), kind=ref.kind,
                        source=ref.source, tags=ref.tags)

    def collapse(self, key: str) -> None:
        """Revert an expanded entry to its summary form."""
        ref = self._cold.get(key)
        if ref is None:
            raise KeyError(f"no cold ref for {key!r}")
        self.add(key, ref.summary, kind="summary",
                 source=ref.source, tags=ref.tags)

    def _make_room(self, needed: int) -> None:
        for key in list(self._hot.keys()):
            if self._used + needed <= self._budget:
                return
            if self._hot[key].pinned:
                continue
            self._used -= self._hot[key].tokens
            del self._hot[key]
        if self._used + needed > self._budget:
            raise WorkingSetBudgetError(
                "cannot fit entry: all remaining entries are pinned")
