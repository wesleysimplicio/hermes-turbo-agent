"""Delta-encoded context builder.

Conversation context is append-only most of the time. Re-sending the full
prompt on every turn is wasteful: the LLM provider already has the prefix in
its prompt cache and we already tokenized it locally. This module tracks the
last prefix that was emitted and yields only the new suffix.

Safety:
- The prefix is identified by a stable SHA-256 of its serialized messages.
- If the new context diverges from the recorded prefix (edit, branch, model
  change), the builder transparently falls back to a full rebuild.
- Reset is automatic when the caller passes a different ``namespace``
  (e.g. a different conversation id, model, or tokenizer fingerprint).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Iterable, Optional, Sequence


def _hash_messages(messages: Sequence[dict]) -> str:
    """Stable hash over a list of message dicts."""
    payload = json.dumps(messages, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ContextDelta:
    """Result of an incremental build."""

    namespace: str
    prefix_hash: str
    new_messages: tuple
    is_full_rebuild: bool

    @property
    def has_new_content(self) -> bool:
        return bool(self.new_messages)


@dataclass
class IncrementalContextBuilder:
    """Tracks the last emitted prefix per ``namespace`` and emits only deltas.

    A ``namespace`` is any string that scopes a conversation. Convention:
    ``"{conversation_id}:{model}:{tokenizer_fingerprint}"``. Changing any
    component invalidates the cached prefix and forces a full rebuild.
    """

    _prefix_hash_by_ns: dict = field(default_factory=dict)
    _prefix_len_by_ns: dict = field(default_factory=dict)

    def build(self, namespace: str, messages: Sequence[dict]) -> ContextDelta:
        """Return the delta for ``messages`` under ``namespace``."""
        if not messages:
            return ContextDelta(namespace, "", tuple(), is_full_rebuild=False)

        last_hash = self._prefix_hash_by_ns.get(namespace)
        last_len = self._prefix_len_by_ns.get(namespace, 0)

        if last_hash and last_len <= len(messages):
            prefix_now = _hash_messages(list(messages[:last_len]))
            if prefix_now == last_hash:
                new = tuple(messages[last_len:])
                new_hash = _hash_messages(list(messages))
                self._prefix_hash_by_ns[namespace] = new_hash
                self._prefix_len_by_ns[namespace] = len(messages)
                return ContextDelta(
                    namespace=namespace,
                    prefix_hash=new_hash,
                    new_messages=new,
                    is_full_rebuild=False,
                )

        # Divergence or first call: full rebuild.
        full_hash = _hash_messages(list(messages))
        self._prefix_hash_by_ns[namespace] = full_hash
        self._prefix_len_by_ns[namespace] = len(messages)
        return ContextDelta(
            namespace=namespace,
            prefix_hash=full_hash,
            new_messages=tuple(messages),
            is_full_rebuild=True,
        )

    def reset(self, namespace: Optional[str] = None) -> None:
        """Invalidate one namespace (or all if ``namespace`` is None)."""
        if namespace is None:
            self._prefix_hash_by_ns.clear()
            self._prefix_len_by_ns.clear()
            return
        self._prefix_hash_by_ns.pop(namespace, None)
        self._prefix_len_by_ns.pop(namespace, None)

    def known_namespaces(self) -> Iterable[str]:
        return tuple(self._prefix_hash_by_ns.keys())
