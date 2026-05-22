"""Regression tests for the Sprint 3 brand-consistency pass (issue #43).

Ensures user-facing surfaces lead with "Tota Agent" instead of the
inherited "Hermes Agent" branding. The fork still describes itself as
*a modified, faster Hermes* — that exact phrasing is intentional and
should NOT be flagged.
"""

from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def test_default_skin_says_tota_agent():
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from hermes_cli.skin_engine import load_skin

    skin = load_skin("default")
    assert skin.get_branding("agent_name", "") == "Tota Agent"
    welcome = skin.get_branding("welcome", "")
    assert "Tota Agent" in welcome
    assert "Hermes" in welcome  # tagline keeps the lineage explicit
    assert skin.get_branding("response_label", "").strip() == "⚕ Tota"


def test_default_identity_introduces_tota():
    import sys

    sys.path.insert(0, str(REPO_ROOT))
    from agent.prompt_builder import DEFAULT_AGENT_IDENTITY

    assert "Tota Agent" in DEFAULT_AGENT_IDENTITY
    assert "modified and faster Hermes" in DEFAULT_AGENT_IDENTITY


def test_pyproject_ships_tota_console_script_aliases():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    assert 'tota = "hermes_cli.main:main"' in pyproject
    assert 'tota-agent = "run_agent:main"' in pyproject
    assert 'tota-acp = "acp_adapter.entry:main"' in pyproject
    # Back-compat: hermes alias must still exist.
    assert 'hermes = "hermes_cli.main:main"' in pyproject


def test_pyproject_describes_tota_in_description():
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    assert "Tota Agent" in pyproject
    assert 'description = "Tota Agent' in pyproject


def test_local_tota_home_version_matches_pyproject():
    version_file = REPO_ROOT / ".tota" / "version"
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    expected = version_file.read_text().strip()
    assert f'version = "{expected}"' in pyproject


def test_identity_customization_doc_exists():
    doc = REPO_ROOT / "docs" / "tota-identity-customization.md"
    assert doc.exists()
    text = doc.read_text()
    assert "SOUL.md" in text
    assert "TOTA_HOME" in text


def test_pypi_adr_exists():
    adr = REPO_ROOT / "docs" / "adr" / "0001-pypi-publishing.md"
    assert adr.exists()
    text = adr.read_text()
    # ADR must commit to an option.
    assert "## Decision" in text
