"""
cache.py — embedding cache keyed by content HASH.

Why hash, not file: if a code block didn't change, the hash is the same ->
reuse the vector. File changes but the relevant snippet didn't? Still a
cache hit. Snippet changes -> new hash -> only that one is re-embedded. Granular.

Persisted in .simplicio/emb_cache.npz (vectors) + .json (hash->row index).
"""

import os, json, hashlib

# numpy is imported lazily (inside the methods that need it) so this module
# stays importable in the host repo without the optional embedding stack.
# Behaviour is identical once numpy is installed — see simplicio.embeddings in
# tools/lazy_deps.py for the on-demand install path.

class EmbeddingCache:
    def __init__(self, root):
        self.dir = os.path.join(root, ".simplicio")
        os.makedirs(self.dir, exist_ok=True)
        self.vec_path = os.path.join(self.dir, "emb_cache.npz")
        self.idx_path = os.path.join(self.dir, "emb_index.json")
        self.index = {}        # hash -> row position in the matrix
        self.vectors = None    # np.ndarray [N, dim]
        self._load()

    @staticmethod
    def h(text):
        return hashlib.sha1(text.encode("utf-8")).hexdigest()

    def _load(self):
        if os.path.exists(self.idx_path) and os.path.exists(self.vec_path):
            import numpy as np
            self.index = json.load(open(self.idx_path, encoding="utf-8"))
            self.vectors = np.load(self.vec_path)["v"]

    def save(self):
        import numpy as np
        json.dump(self.index, open(self.idx_path, "w", encoding="utf-8"))
        if self.vectors is not None:
            np.savez_compressed(self.vec_path, v=self.vectors)

    def get_missing(self, texts):
        """Returns the texts NOT in the cache (need embedding)."""
        return [t for t in texts if self.h(t) not in self.index]

    def add(self, texts, vectors):
        """Adds new texts+vectors to the cache."""
        if not texts:
            return
        import numpy as np
        vectors = np.asarray(vectors)
        base = 0 if self.vectors is None else self.vectors.shape[0]
        self.vectors = vectors if self.vectors is None else np.vstack([self.vectors, vectors])
        for i, t in enumerate(texts):
            self.index[self.h(t)] = base + i

    def lookup(self, texts):
        """Returns a matrix of vectors in the texts' order (all already cached)."""
        rows = [self.index[self.h(t)] for t in texts]
        return self.vectors[rows]

    def stats(self):
        return {"cached_blocks": len(self.index),
                "dim": 0 if self.vectors is None else int(self.vectors.shape[1])}
