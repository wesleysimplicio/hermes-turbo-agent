"""skill_router tests — loading + the numpy-free no-skills short-circuit."""

import os

from simplicio import skill_router


def _write_skill(d, name, text):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        fh.write(text)


def test_skills_dir_default(tmp_path):
    assert skill_router._skills_dir(str(tmp_path)) == os.path.join(
        str(tmp_path), ".mapper", "skills"
    )


def test_skills_dir_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("SIMPLICIO_SKILLS_DIR", "/custom/skills")
    assert skill_router._skills_dir(str(tmp_path)) == "/custom/skills"


def test_load_skills_reads_description_and_body(tmp_path, monkeypatch):
    sdir = str(tmp_path / "skills")
    monkeypatch.setenv("SIMPLICIO_SKILLS_DIR", sdir)
    _write_skill(sdir, "perm.md", "# Hide elements by permission\n\nbody text\n")
    _write_skill(sdir, "blank.md", "\n\nGuard routes by role\n")

    skills = skill_router._load_skills(str(tmp_path))
    by_name = {s["name"]: s for s in skills}
    assert by_name["perm.md"]["desc"] == "Hide elements by permission"
    assert "body text" in by_name["perm.md"]["body"]
    # First *non-empty* line, with leading '#'/spaces stripped.
    assert by_name["blank.md"]["desc"] == "Guard routes by role"


def test_build_skill_block_empty_when_no_skills(tmp_path, monkeypatch):
    # Point at an empty dir; no skills -> layer disappears, numpy never imported.
    monkeypatch.setenv("SIMPLICIO_SKILLS_DIR", str(tmp_path / "nope"))
    assert skill_router.build_skill_block(str(tmp_path), "any task") == ""
