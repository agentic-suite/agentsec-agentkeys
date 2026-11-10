"""The install story must not tell a reader to run something that does not work yet."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")
ADOPTION = (REPO / "docs" / "guides" / "adoption-paths.md").read_text(encoding="utf-8")
QUICKSTART = (REPO / "docs" / "tutorials" / "quickstart.md").read_text(encoding="utf-8")


def test_the_readme_documents_the_published_pypi_install() -> None:
    assert "pip install agentsec-agentkeys" in README
    assert "not on pypi" not in README.lower(), (
        "the package is published — the stale caveat must go"
    )


def test_the_readme_gives_a_working_install_path_today() -> None:
    assert "pip install ." in README or "pip install -e" in README, (
        "from-source install must be shown"
    )


def test_the_readme_does_not_call_init_a_working_step() -> None:
    section = README[README.index("## Install & run") : README.index("### Reserved exit codes")]
    if "agentkeys init" in section:
        assert "stub" in section.lower(), "init exits 1 — it cannot be part of a quick install"


def test_adoption_paths_starts_from_the_published_install() -> None:
    assert "pip install agentsec-agentkeys" in ADOPTION


def test_adoption_paths_does_not_sell_init_as_the_first_step() -> None:
    assert "agentkeys init" not in ADOPTION.replace("`agentkeys init`", "agentkeys-init"), (
        "init is an honest stub; the adoption path must start from a written config"
    )


def test_the_quickstart_is_install_agnostic() -> None:
    """The quickstart runs from a checkout in CI, so it must not depend on the published package."""
    assert "pip install agentsec-agentkeys" not in QUICKSTART


def test_the_cli_reference_marks_the_stubs_as_stubs() -> None:
    cli = (REPO / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    for row in cli.splitlines():
        if "`agentkeys init`" in row or "`agentkeys context-dump" in row:
            assert "stub" in row.lower(), f"stub not marked: {row[:70]}"


def test_the_readme_has_the_suite_badges() -> None:
    for badge in (
        "actions/workflows/ci.yml/badge.svg",
        "license-Apache--2.0",
        "python-3.11",
        "status-release%20candidate",
        "field--tested",
        "release-unsigned",
        "mypy-strict",
        "securityscorecards.dev/projects/github.com/agentic-suite/agentsec-agentkeys",
    ):
        assert badge in README, f"missing badge: {badge}"


def test_the_audit_workflow_pins_the_scanner_versions() -> None:
    workflow = (REPO / ".github" / "workflows" / "release-audit.yml").read_text(encoding="utf-8")
    assert "GITLEAKS_VERSION=8.30.1" in workflow
    assert "TRUFFLEHOG_VERSION=3.99.8" in workflow
