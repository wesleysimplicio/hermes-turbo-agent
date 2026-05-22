"""Unit tests for :mod:`agent.registry.skill_meta`."""

from __future__ import annotations

from pathlib import Path

import pytest

from agent.registry.skill_meta import SkillManifest, SkillRegistry


SAMPLE_BODY = "# Sample\n\n## Trigger\nX\n\n## Steps\n1. A\n2. B\n"


def test_register_stores_only_manifest():
    reg = SkillRegistry()
    calls = []
    reg.register("s", "trig", "summ", lambda: (calls.append(1), SAMPLE_BODY)[1])
    assert reg.list() == [SkillManifest("s", "trig", "summ")]
    assert calls == []
    assert reg.stats() == {"registered": 1, "loaded": 0}


def test_load_body_caches_first_call():
    reg = SkillRegistry()
    calls = []

    def loader():
        calls.append(1)
        return SAMPLE_BODY

    reg.register("s", "t", "s", loader)
    assert reg.load_body("s") is reg.load_body("s")
    assert calls == [1]


def test_register_path_lazy_reads_file(tmp_path: Path):
    body_path = tmp_path / "SKILL.md"
    body_path.write_text(SAMPLE_BODY, encoding="utf-8")
    reg = SkillRegistry()
    reg.register_path("d", "t", "s", body_path)
    assert reg.stats() == {"registered": 1, "loaded": 0}
    assert reg.load_body("d") == SAMPLE_BODY
    assert reg.stats() == {"registered": 1, "loaded": 1}


def test_validation_errors():
    reg = SkillRegistry()
    with pytest.raises(ValueError):
        reg.register("", "t", "s", lambda: "")
    with pytest.raises(TypeError):
        reg.register("x", "t", "s", "not-callable")  # type: ignore[arg-type]
    reg.register("bad", "t", "s", lambda: 123)  # type: ignore[arg-type,return-value]
    with pytest.raises(TypeError):
        reg.load_body("bad")
    with pytest.raises(KeyError):
        reg.load_body("missing")


def test_default_registry_helpers():
    from agent.registry import skill_meta as mod

    mod._reset_default_registry_for_tests()
    mod.register_skill("s1", "t", "s", lambda: "body")
    assert [s.name for s in mod.list_skills()] == ["s1"]
    assert mod.load_skill_body("s1") == "body"
    mod._reset_default_registry_for_tests()
