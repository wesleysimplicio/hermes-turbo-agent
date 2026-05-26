"""
precedent.py — finds PRECEDENT using the cache (only embeds new blocks).
"""
import re, glob, os
from .cache import EmbeddingCache

# numpy / sentence-transformers are imported lazily inside the functions that
# need them so this module imports cleanly without the optional embedding
# stack (lazy-installed via simplicio.embeddings in tools/lazy_deps.py).

_emb = None
def _embedder():
    global _emb
    if _emb is None:
        from sentence_transformers import SentenceTransformer
        _emb = SentenceTransformer("all-MiniLM-L6-v2")
    return _emb

PATTERNS = {
    "angular": [r"\*ngIf", r"\[hidden\]", r"\[disabled\]", r"hasPerm",
                r"ngxPermission", r"canActivate"],
    "react":   [r"&&\s*<", r"\?\s*<[A-Z]", r"usePermission", r"\bcan\(",
                r"hasRole", r"<Protected"],
    "dotnet":  [r"\[Authorize", r"HasPermission", r"User\.IsInRole",
                r"\[HasPolicy", r"RequireClaim"],
}
EXT = {"angular": (".html", ".ts"), "react": (".tsx", ".jsx", ".ts"),
       "dotnet": (".cs", ".cshtml", ".razor")}
SKIP = ("node_modules", "/.git/", "/dist/", "/bin/", "/obj/", "/.angular/", "/.simplicio/")


def grep_candidates(root, stack, window=1):
    pats = [re.compile(p) for p in PATTERNS[stack]]
    exts = EXT[stack]
    cands = []
    for fp in glob.glob(f"{root}/**/*", recursive=True):
        if not os.path.isfile(fp) or not fp.endswith(exts): continue
        if any(s in fp for s in SKIP): continue
        try:
            lines = open(fp, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        for i, ln in enumerate(lines):
            if any(p.search(ln) for p in pats):
                block = "\n".join(lines[max(0, i - window): i + window + 1])
                cands.append({"file": fp, "line": i + 1, "code": block})
    return cands


def index_repo(root, stack, verbose=True):
    """Index: embed ONLY new blocks, persist cache. Returns stats."""
    cache = EmbeddingCache(root)
    cands = grep_candidates(root, stack)
    texts = list({c["code"] for c in cands})         # dedup
    missing = cache.get_missing(texts)
    if missing:
        vectors = _embedder().encode(missing, show_progress_bar=False)
        cache.add(missing, vectors)
        cache.save()
    if verbose:
        print(f"[index] candidates={len(cands)} newly_embedded={len(missing)} "
              f"cache_total={cache.stats()['cached_blocks']}")
    return cache, cands


def build_precedent_block(root, stack, task, k=2):
    cache, cands = index_repo(root, stack, verbose=False)
    if not cands:
        return "[PRECEDENT]\n(no similar pattern in repo — generate from scratch using stack convention)"
    import numpy as np
    texts = [c["code"] for c in cands]
    vc = cache.lookup(texts)                           # from cache, no re-embed
    vt = _embedder().encode([task])[0]                 # only the task (short)
    for c, v in zip(cands, vc):
        c["score"] = float(np.dot(vt, v) / (np.linalg.norm(vt) * np.linalg.norm(v)))
    seen, out = set(), []
    for c in sorted(cands, key=lambda x: x["score"], reverse=True):
        if c["code"] in seen: continue
        seen.add(c["code"]); out.append(c)
    tops = out[:k]
    lines = ["[PRECEDENT]",
             "This project ALREADY does something similar. Follow THIS convention, don't invent:"]
    for c in tops:
        rel = os.path.relpath(c["file"], root)
        lines.append(f"\n# {rel}:{c['line']}  (similarity {c['score']:.2f})")
        lines.append(c["code"])
    return "\n".join(lines)
