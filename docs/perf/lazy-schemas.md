# Lazy Tool Schemas & Skill Metadata

## Motivation

Tool JSON schemas and full SKILL.md bodies dominate the cold prompt.
Hundreds of tools and dozens of skills get advertised even when a turn
uses a handful. `agent/registry/` publishes only the lightweight surface
at startup and loads the heavy payload on first use.

## Components

- `agent.registry.lazy_schema` — `ToolStub(name, description)` registry.
  Full JSON schema produced by a `schema_loader` callable and cached on
  the first call to `load_schema(name)`.
- `agent.registry.skill_meta` — `SkillManifest(name, trigger,
  steps_summary)` registry. Full SKILL.md body produced by a
  `body_loader` (or via `register_path`) and cached on the first call
  to `load_skill_body(name)`. Thread-safe; exposes `stats()` and `clear()`.

## Usage

```python
from agent.registry import register_tool, list_tools, load_schema

register_tool("search", "Search the web.",
              lambda: {"type": "object",
                       "properties": {"q": {"type": "string"}}})
stubs = list_tools()           # [ToolStub("search", "Search the web.")]
schema = load_schema("search") # full JSON, cached
```

Skills mirror the API via `register_skill` / `list_skills` /
`load_skill_body`. For on-disk SKILL.md, use
`SkillRegistry.register_path(name, trigger, summary, path)`.

## Expected savings

A stub is ~80-200 B; a full schema 0.6-6 KB. For 200 tools, the cold
tool surface drops from ~600 KB to ~30 KB. Skill bodies typically weigh
2-10 KB vs. <200 B for a manifest.

## Notes

- Loaders run outside the internal lock; concurrent readers are not blocked.
- Re-registering a name invalidates the cached payload.
- Loader exceptions propagate; no negative caching.
