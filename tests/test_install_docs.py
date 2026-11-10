"""The install story must not tell a reader to run something that does not work yet."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")
ADOPTION = (REPO / "docs" / "guides" / "adoption-paths.md").read_text(encoding="utf-8")
QUICKSTART = (REPO / "docs" / "tutorials" / "quickstart.md").read_text(encoding="utf-8")


def test_the_readme_says_the_package_is_not_on_pypi_yet() -> None:
    lowered = README.lower()
    assert "not on pypi" in lowered or "not yet published to pypi" in lowered, (
        "a `pip install agentsec-agentkeys` line is a false instruction until the upload happens"
    )


def test_the_readme_gives_a_working_install_path_today() -> None:
    assert "pip install ." in README or "pip install -e" in README, "from-source install must be shown"


def test_the_readme_does_not_call_init_a_working_step() -> None:
    section = README[README.index("## Install & run") : README.index("### Reserved exit codes")]
    if "agentkeys init" in section:
        assert "stub" in section.lower(), "init exits 1 — it cannot be part of a quick install"


def test_adoption_paths_does_not_promise_a_pip_install_that_fails() -> None:
    for line in ADOPTION.splitlines():
        if "pip install agentsec-agentkeys" in line:
            raise AssertionError(
                "adoption-paths still instructs a PyPI install before the package is published: "
                f"{line.strip()}"
            )


def test_adoption_paths_does_not_sell_init_as_the_first_step() -> None:
    assert "agentkeys init" not in ADOPTION.replace("`agentkeys init`", "agentkeys-init"), (
        "init is an honest stub; the adoption path must start from a written config"
    )


def test_the_quickstart_does_not_require_a_published_package() -> None:
    assert "pip install agentsec-agentkeys" not in QUICKSTART


def test_the_cli_reference_marks_the_stubs_as_stubs() -> None:
    cli = (REPO / "docs" / "reference" / "cli.md").read_text(encoding="utf-8")
    for row in cli.splitlines():
        if "`agentkeys init`" in row or "`agentkeys context-dump" in row:
            assert "stub" in row.lower(), f"stub not marked: {row[:70]}"
