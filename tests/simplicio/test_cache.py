"""EmbeddingCache tests. Hash + membership are numpy-free; the vector
round-trip is guarded by ``importorskip`` since numpy is an optional dep."""

import hashlib
import os

import pytest

from simplicio.cache import EmbeddingCache


def test_hash_is_sha1():
    assert EmbeddingCache.h("abc") == hashlib.sha1(b"abc").hexdigest()


def test_get_missing_when_empty(tmp_path):
    cache = EmbeddingCache(str(tmp_path))
    assert cache.get_missing(["x", "y"]) == ["x", "y"]
    assert cache.stats() == {"cached_blocks": 0, "dim": 0}
    # Cache dir is created under the repo root.
    assert os.path.isdir(os.path.join(str(tmp_path), ".simplicio"))


def test_add_lookup_roundtrip_and_persist(tmp_path):
    np = pytest.importorskip("numpy")
    root = str(tmp_path)
    cache = EmbeddingCache(root)
    texts = ["alpha", "beta"]
    vecs = np.asarray([[1.0, 0.0], [0.0, 1.0]])
    cache.add(texts, vecs)
    cache.save()

    assert cache.get_missing(texts) == []
    np.testing.assert_allclose(cache.lookup(["beta", "alpha"]), [[0.0, 1.0], [1.0, 0.0]])
    assert cache.stats() == {"cached_blocks": 2, "dim": 2}

    # A fresh instance reloads the persisted vectors + index.
    reloaded = EmbeddingCache(root)
    assert reloaded.get_missing(texts) == []
    np.testing.assert_allclose(reloaded.lookup(["alpha"]), [[1.0, 0.0]])


def test_add_noop_on_empty(tmp_path):
    cache = EmbeddingCache(str(tmp_path))
    cache.add([], None)  # must not raise / must not import numpy
    assert cache.stats()["cached_blocks"] == 0
