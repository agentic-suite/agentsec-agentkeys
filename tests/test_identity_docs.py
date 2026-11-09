"""0.7 — repo identity & governance docs are finalized and self-consistent."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_readme_documents_install_and_home() -> None:
    readme = _read("README.md")
    assert "pip install agentsec-agentkeys" in readme
    assert "AGENTKEYS_HOME" in readme


def test_readme_documents_the_built_surface() -> None:
    readme = _read("README.md")
    for token in ("agentkeys --help", "agentkeys doctor", "agentkeys scan", "agentkeys revoke"):
        assert token in readme, token


def test_readme_states_the_reserved_exit_codes() -> None:
    readme = _read("README.md")
    assert "0" in readme and "denied" in readme and "tamper" in readme
    assert "revoke-verified" in readme.lower() or "revoke verified" in readme.lower()


def test_readme_states_the_unsupported_platform() -> None:
    readme = _read("README.md")
    assert "Windows" in readme


def test_readme_documents_references_only_config() -> None:
    readme = _read("README.md")
    lowered = readme.lower()
    assert "reference" in lowered
    assert "never a secret" in lowered or "references only" in lowered


def test_readme_points_at_the_design_doc() -> None:
    assert "docs/design/v0.1.0/foundation.md" in _read("README.md")


def test_license_is_apache_2() -> None:
    license_text = _read("LICENSE")
    assert "Apache License" in license_text
    assert "Version 2.0" in license_text


def test_codeowners_has_no_placeholder() -> None:
    codeowners = _read("CODEOWNERS")
    assert "Replace with the maintainer" not in codeowners
    assert "@deghosal-2026" in codeowners


def test_contributing_points_at_the_prd_set_not_a_vault_path() -> None:
    contributing = _read("CONTRIBUTING.md")
    assert "docs/prd/" in contributing
    assert "research/agent-security" not in contributing


def test_security_policy_forbids_public_issues() -> None:
    security = _read("SECURITY.md")
    assert "Do not open public issues" in security
    assert "privately" in security


def test_agents_md_marks_reports_hand_maintained() -> None:
    agents = _read("AGENTS.md")
    assert "HAND-MAINTAINED" in agents or "hand-maintained" in agents
    assert "field-test" in agents.lower()