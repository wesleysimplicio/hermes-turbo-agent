"""Deterministic project fingerprint via manifest heuristics.

Walks the repository root for well-known manifest files and emits a
``ProjectFingerprint`` describing stack, package manager, language,
monorepo workspaces, and entry-point hints. No AST, no embeddings,
no network. Pure stdlib so it runs in every adapter and the warm
daemon cold-start.

Why heuristic-by-manifest:
    90% of "what stack is this" signal lives in declared manifests.
    Reading them is O(n_manifests) bytes — orders of magnitude cheaper
    than scanning source. Feeds the no-LLM router (#99) and the
    working set (#92) without paying an LLM round-trip.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_MANIFESTS: Tuple[Tuple[str, str], ...] = (
    ("package.json", "node"),
    ("pyproject.toml", "python"),
    ("setup.py", "python"),
    ("requirements.txt", "python"),
    ("go.mod", "go"),
    ("Cargo.toml", "rust"),
    ("pom.xml", "java"),
    ("build.gradle", "java"),
    ("build.gradle.kts", "kotlin"),
    ("Gemfile", "ruby"),
    ("composer.json", "php"),
    ("mix.exs", "elixir"),
    ("pubspec.yaml", "dart"),
    ("Package.swift", "swift"),
    ("deno.json", "deno"),
    ("deno.jsonc", "deno"),
)

_PKG_MANAGER_LOCKS: Tuple[Tuple[str, str], ...] = (
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("package-lock.json", "npm"),
    ("bun.lockb", "bun"),
    ("uv.lock", "uv"),
    ("poetry.lock", "poetry"),
    ("Pipfile.lock", "pipenv"),
    ("Cargo.lock", "cargo"),
    ("go.sum", "go-modules"),
    ("Gemfile.lock", "bundler"),
)

_FRAMEWORK_PATTERNS: Dict[str, Tuple[str, ...]] = {
    "next": ("next",),
    "react": ("react",),
    "vue": ("vue",),
    "svelte": ("svelte", "@sveltejs/kit"),
    "express": ("express",),
    "fastapi": ("fastapi",),
    "django": ("django",),
    "flask": ("flask",),
    "rails": ("rails",),
    "spring": ("spring-boot-starter",),
    "axum": ("axum",),
    "actix": ("actix-web",),
    "tokio": ("tokio",),
    "anthropic": ("anthropic",),
    "openai": ("openai",),
}

_AUTH_PATTERNS: Tuple[str, ...] = (
    "next-auth",
    "passport",
    "auth0",
    "clerk",
    "supabase",
    "firebase-auth",
    "authlib",
    "python-jose",
    "django-allauth",
    "devise",
)

_DB_PATTERNS: Tuple[str, ...] = (
    "postgres", "psycopg", "asyncpg", "pg",
    "mysql", "mariadb",
    "mongodb", "mongoose",
    "redis", "aioredis",
    "sqlalchemy", "tortoise-orm",
    "prisma",
    "sqlite", "better-sqlite3",
)

_PYPROJECT_DEPS_RE = re.compile(
    r"^(?:dependencies|optional-dependencies)\s*=", re.MULTILINE
)


@dataclass(frozen=True)
class ProjectFingerprint:
    """Immutable view of a project's detected shape."""

    root: str
    languages: Tuple[str, ...] = ()
    manifests: Tuple[str, ...] = ()
    package_managers: Tuple[str, ...] = ()
    frameworks: Tuple[str, ...] = ()
    auth: Tuple[str, ...] = ()
    db: Tuple[str, ...] = ()
    workspaces: Tuple[str, ...] = ()
    is_monorepo: bool = False
    entrypoints: Tuple[str, ...] = ()

    @property
    def primary_language(self) -> Optional[str]:
        return self.languages[0] if self.languages else None


def _read_text(path: Path, limit: int = 1_000_000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        return ""


def _scan_patterns(text: str, patterns: Tuple[str, ...]) -> Tuple[str, ...]:
    hits: List[str] = []
    seen: set[str] = set()
    lowered = text.lower()
    for pat in patterns:
        if pat in lowered and pat not in seen:
            hits.append(pat)
            seen.add(pat)
    return tuple(hits)


def _detect_workspaces(root: Path) -> Tuple[Tuple[str, ...], bool]:
    pkg = root / "package.json"
    if pkg.exists():
        try:
            data = json.loads(_read_text(pkg) or "{}")
            ws = data.get("workspaces")
            if isinstance(ws, dict):
                ws = ws.get("packages")
            if isinstance(ws, list) and ws:
                return tuple(str(w) for w in ws), True
        except (json.JSONDecodeError, ValueError):
            pass

    pnpm_ws = root / "pnpm-workspace.yaml"
    if pnpm_ws.exists():
        text = _read_text(pnpm_ws)
        packages = re.findall(r"^\s*-\s*['\"]?([^'\"\n]+)['\"]?", text, re.MULTILINE)
        if packages:
            return tuple(packages), True

    cargo = root / "Cargo.toml"
    if cargo.exists():
        text = _read_text(cargo)
        m = re.search(
            r"\[workspace\][^\[]*?members\s*=\s*\[([^\]]+)\]", text, re.DOTALL
        )
        if m:
            members = re.findall(r"\"([^\"]+)\"", m.group(1))
            if members:
                return tuple(members), True

    return (), False


def _detect_entrypoints(root: Path) -> Tuple[str, ...]:
    candidates = (
        "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
        "index.js", "index.ts", "server.js", "server.ts",
        "main.go", "cmd",
        "src/main.rs", "src/lib.rs",
        "Cargo.toml",
    )
    hits: List[str] = []
    for name in candidates:
        if (root / name).exists():
            hits.append(name)
    return tuple(hits)


def detect_fingerprint(root: str | Path = ".") -> ProjectFingerprint:
    """Detect a project fingerprint by reading manifests under ``root``.

    Reads only top-level manifests by default. O(few hundred KB) of I/O,
    no recursion. Safe to call on the warm-daemon hot path.
    """

    root_path = Path(root).expanduser().resolve()
    languages: List[str] = []
    manifests: List[str] = []
    lang_seen: set[str] = set()

    for manifest, lang in _MANIFESTS:
        if (root_path / manifest).exists():
            manifests.append(manifest)
            if lang not in lang_seen:
                languages.append(lang)
                lang_seen.add(lang)

    package_managers: List[str] = []
    for lock, pm in _PKG_MANAGER_LOCKS:
        if (root_path / lock).exists():
            package_managers.append(pm)

    haystack_chunks: List[str] = []
    pkg = root_path / "package.json"
    if pkg.exists():
        haystack_chunks.append(_read_text(pkg))
    pyproject = root_path / "pyproject.toml"
    if pyproject.exists():
        haystack_chunks.append(_read_text(pyproject))
    requirements = root_path / "requirements.txt"
    if requirements.exists():
        haystack_chunks.append(_read_text(requirements))
    cargo = root_path / "Cargo.toml"
    if cargo.exists():
        haystack_chunks.append(_read_text(cargo))
    gomod = root_path / "go.mod"
    if gomod.exists():
        haystack_chunks.append(_read_text(gomod))

    haystack = "\n".join(haystack_chunks)

    framework_hits: List[str] = []
    for name, patterns in _FRAMEWORK_PATTERNS.items():
        for pat in patterns:
            if pat in haystack.lower():
                framework_hits.append(name)
                break

    auth_hits = _scan_patterns(haystack, _AUTH_PATTERNS)
    db_hits = _scan_patterns(haystack, _DB_PATTERNS)

    workspaces, is_monorepo = _detect_workspaces(root_path)
    entrypoints = _detect_entrypoints(root_path)

    return ProjectFingerprint(
        root=str(root_path),
        languages=tuple(languages),
        manifests=tuple(manifests),
        package_managers=tuple(package_managers),
        frameworks=tuple(framework_hits),
        auth=auth_hits,
        db=db_hits,
        workspaces=workspaces,
        is_monorepo=is_monorepo,
        entrypoints=entrypoints,
    )


def fingerprint_to_dict(fp: ProjectFingerprint) -> Dict[str, Any]:
    """JSON-safe dict view of the fingerprint."""

    data = asdict(fp)
    data["primary_language"] = fp.primary_language
    return data
