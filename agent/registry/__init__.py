"""Registry helpers for lazy tool schema and skill metadata loading.

See ``docs/perf/lazy-schemas.md``.
"""

from .lazy_schema import (
    LazyToolRegistry, ToolStub, list_tools, load_schema, register_tool,
)
from .skill_meta import (
    SkillManifest, SkillRegistry, list_skills, load_skill_body, register_skill,
)

__all__ = [
    "LazyToolRegistry", "ToolStub", "register_tool", "list_tools", "load_schema",
    "SkillManifest", "SkillRegistry", "register_skill", "list_skills", "load_skill_body",
]
