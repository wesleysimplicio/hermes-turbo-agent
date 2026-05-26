"""prompt.py — stacks the 6 layers."""
import os, re
from .precedent import build_precedent_block
from .skill_router import build_skill_block

def _mapper(root, target):
    try:
        txt = open(os.path.join(root, target), encoding="utf-8", errors="ignore").read()
    except Exception:
        return "(mapper: target not read)"
    deps = [l for l in txt.splitlines()
            if l.strip().startswith(("import", "using", "from"))][:15]
    return f"File: {target}\nDependencies:\n" + "\n".join(deps)

def build_prompt(root, stack, goal, target, criteria, constraints):
    tpl_path = os.path.join(os.path.dirname(__file__), "templates", "simplicio_prompt.md")
    tpl = open(tpl_path, encoding="utf-8").read()
    prec = build_precedent_block(root, stack, goal, k=2)
    skill = build_skill_block(root, goal)
    target_block = f"{target}\n\nTarget context:\n{_mapper(root, target)}"
    for s, v in {"{{STACK}}": stack, "{{GOAL}}": goal,
                 "{{TARGET}}": target_block, "{{PRECEDENT}}": prec, "{{SKILL}}": skill,
                 "{{CRITERIA}}": criteria, "{{CONSTRAINTS}}": constraints}.items():
        tpl = tpl.replace(s, v)
    return re.sub(r"\{#.*?#\}", "", tpl, flags=re.DOTALL).strip()
