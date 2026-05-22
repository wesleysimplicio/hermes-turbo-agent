"""Tests for ``agent.project_mapper.fingerprint``."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest

from agent.project_mapper import detect_fingerprint, fingerprint_to_dict


def _w(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")


def test_detects_python_via_pyproject(tmp_path: Path) -> None:
    _w(tmp_path / "pyproject.toml", """
        [project]
        name = "foo"
        dependencies = ["fastapi", "sqlalchemy"]
    """)
    _w(tmp_path / "uv.lock", "version = 1\n")

    fp = detect_fingerprint(tmp_path)
    assert "python" in fp.languages
    assert fp.primary_language == "python"
    assert "pyproject.toml" in fp.manifests
    assert "uv" in fp.package_managers
    assert "fastapi" in fp.frameworks
    assert "sqlalchemy" in fp.db


def test_detects_node_with_workspaces(tmp_path: Path) -> None:
    _w(tmp_path / "package.json", json.dumps({
        "name": "root",
        "private": True,
        "workspaces": ["packages/*"],
        "dependencies": {"next": "^14", "next-auth": "^4"},
    }))
    _w(tmp_path / "pnpm-lock.yaml", "lockfileVersion: 9\n")

    fp = detect_fingerprint(tmp_path)
    assert "node" in fp.languages
    assert "pnpm" in fp.package_managers
    assert "next" in fp.frameworks
    assert "next-auth" in fp.auth
    assert fp.is_monorepo is True
    assert fp.workspaces == ("packages/*",)


def test_detects_rust_workspace(tmp_path: Path) -> None:
    _w(tmp_path / "Cargo.toml", """
        [workspace]
        members = ["crates/a", "crates/b"]

        [workspace.dependencies]
        tokio = "1.0"
        axum = "0.7"
    """)
    _w(tmp_path / "Cargo.lock", "version = 3\n")

    fp = detect_fingerprint(tmp_path)
    assert "rust" in fp.languages
    assert fp.is_monorepo is True
    assert fp.workspaces == ("crates/a", "crates/b")
    assert "tokio" in fp.frameworks
    assert "axum" in fp.frameworks


def test_empty_directory(tmp_path: Path) -> None:
    fp = detect_fingerprint(tmp_path)
    assert fp.languages == ()
    assert fp.manifests == ()
    assert fp.primary_language is None
    assert fp.is_monorepo is False


def test_fingerprint_to_dict_is_json_safe(tmp_path: Path) -> None:
    _w(tmp_path / "go.mod", "module example.com/foo\n\ngo 1.22\n")
    fp = detect_fingerprint(tmp_path)
    data = fingerprint_to_dict(fp)
    json.dumps(data)  # raises if not serialisable
    assert data["primary_language"] == "go"
    assert "go.mod" in data["manifests"]


def test_detects_entrypoints(tmp_path: Path) -> None:
    _w(tmp_path / "main.py", "print('hi')\n")
    _w(tmp_path / "package.json", "{}")
    _w(tmp_path / "server.ts", "export {}\n")

    fp = detect_fingerprint(tmp_path)
    assert "main.py" in fp.entrypoints
    assert "server.ts" in fp.entrypoints
