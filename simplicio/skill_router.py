"""
skill_router.py — LAYER 4.5. Picks THE skill that matches the task.
Does NOT inject all of them (noise). Ranks by meaning, takes top-1.

Skill source: by default scans <root>/.mapper/skills/*.md or
SIMPLICIO_SKILLS_DIR. Each skill = md file whose first line is the description.
Reuses the same embedding cache.
"""
import os, glob
from .cache import EmbeddingCache

# numpy is imported lazily (inside build_skill_block) so this module imports
# cleanly without the optional embedding stack.

def _skills_dir(root):
    return os.environ.get("SIMPLICIO_SKILLS_DIR",
                          os.path.join(root, ".mapper", "skills"))

def _load_skills(root):
    d = _skills_dir(root)
    out = []
    for fp in glob.glob(os.path.join(d, "*.md")):
        try:
            txt = open(fp, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        desc = next((l.strip("# ").strip() for l in txt.splitlines() if l.strip()), "")
        out.append({"name": os.path.basename(fp), "desc": desc, "body": txt})
    return out

def build_skill_block(root, task, threshold=0.15):
    skills = _load_skills(root)
    if not skills:
        return ""  # no skills -> layer disappears, no noise
    import numpy as np
    from .precedent import _embedder
    cache = EmbeddingCache(root)
    descs = [s["desc"] for s in skills]
    missing = cache.get_missing(descs)
    if missing:
        cache.add(missing, _embedder().encode(missing, show_progress_bar=False))
        cache.save()
    vd = cache.lookup(descs)
    vt = _embedder().encode([task])[0]
    scores = [float(np.dot(vt, v)/(np.linalg.norm(vt)*np.linalg.norm(v))) for v in vd]
    i = int(np.argmax(scores))
    if scores[i] < threshold:
        return ""  # nothing matches enough -> don't force an irrelevant skill
    s = skills[i]
    return (f"[RELEVANT SKILL]\nThe mapper has a method that matches this task "
            f"(match {scores[i]:.2f}). Follow it:\n# {s['name']}\n{s['body'][:1200]}")
