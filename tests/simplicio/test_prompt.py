"""Prompt-stacking tests for the vendored simplicio 6-layer contract.

These exercise the network-free / numpy-free path: with no precedent matches
and no skills, ``build_prompt`` produces the full layered prompt without
importing the embedding stack.
"""

import os

from simplicio import prompt as prompt_mod
from simplicio import precedent as precedent_mod


def _write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or root, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def test_build_prompt_no_precedent_path_is_numpy_free(tmp_path):
    root = str(tmp_path)
    _write(root, "a.html", "<button>Delete</button>\n")  # no angular auth pattern

    out = prompt_mod.build_prompt(
        root, "angular", "hide Delete for non-admins",
        "a.html", "- admin: present\n- non-admin: absent", "- build passes",
    )

    # All six layers present, every slot substituted, jinja-style comments gone.
    assert "[GOAL]" in out
    assert "hide Delete for non-admins" in out
    assert "Touch ONLY these files:" in out and "a.html" in out
    assert "[PRECEDENT]" in out and "no similar pattern" in out
    assert "[CONTRACT]" in out and "non-admin: absent" in out
    assert "Constraints (do not break):" in out and "build passes" in out
    assert "[OUTPUT]" in out and "Unified DIFF" in out
    assert "{{" not in out and "}}" not in out
    assert "{#" not in out and "#}" not in out
    # No SKILL block when there are no skills.
    assert "[RELEVANT SKILL]" not in out


def test_mapper_extracts_dependencies(tmp_path):
    root = str(tmp_path)
    _write(
        root, "comp.ts",
        "import { Component } from '@angular/core';\n"
        "import { Svc } from './svc';\n"
        "export class C {}\n",
    )
    block = prompt_mod._mapper(root, "comp.ts")
    assert "File: comp.ts" in block
    assert "import { Component }" in block
    assert "import { Svc }" in block


def test_mapper_handles_missing_target(tmp_path):
    block = prompt_mod._mapper(str(tmp_path), "does-not-exist.ts")
    assert block == "(mapper: target not read)"


def test_grep_candidates_finds_angular_auth_patterns(tmp_path):
    root = str(tmp_path)
    _write(root, "ok.html", '<div *ngIf="hasPerm(\'admin\')">x</div>\n')
    _write(root, "plain.html", "<p>nothing</p>\n")
    _write(root, "node_modules/skip.html", '<div *ngIf="x">y</div>\n')  # skipped dir

    cands = precedent_mod.grep_candidates(root, "angular")
    files = {os.path.basename(c["file"]) for c in cands}
    assert "ok.html" in files
    assert "plain.html" not in files
    assert "skip.html" not in files  # node_modules excluded
    assert all("code" in c and "line" in c for c in cands)
