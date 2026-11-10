"""15.4 — the release notes must cite the field journal and name the gaps, not smooth them."""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOTES = REPO / "docs" / "release" / "v0.1.0" / "RELEASE_NOTES.md"


def _notes() -> str:
    return NOTES.read_text(encoding="utf-8")


def test_the_notes_exist_and_carry_version_and_status() -> None:
    text = _notes()
    assert text.startswith("# agentkeys 0.1.0")
    assert "not released" in text.lower() or "release candidate" in text.lower()


def test_the_notes_cite_the_hand_maintained_field_journal() -> None:
    text = _notes()
    assert "FIELD_TEST_REPORT.md" in text
    assert "71" in text and "0 FAIL" in text and "3 WARN" in text
    assert "hand-maintained" in text


def test_the_five_blocking_scenarios_are_named_as_passing() -> None:
    text = _notes()
    for case in (
        "FT-RK-KILLTIME",
        "FT-AP-CONTEXTDUMP",
        "FT-AP-TAMPER",
        "FT-AP-EVIDENCE",
        "FT-MP-SCANMIGRATE",
    ):
        assert case in text


def test_every_remaining_warn_is_named_with_its_limitation() -> None:
    text = _notes()
    for case in ("FT-CL-FIRST", "FT-HC-CLAUDE", "FT-HC-CURSOR"):
        assert case in text
    assert "not logged in" in text.lower()
    assert "no headless" in text.lower()
    assert "naive" in text.lower() or "fresh machine" in text.lower()


def test_the_gap_list_matches_the_roadmap() -> None:
    text = _notes().lower()
    for gap in (
        "sso",
        "multi-tenant",
        "certification",
        "fleet",
        "cloud backends",
        "windows",
        "dpop",
    ):
        assert gap in text, f"the honest gap list dropped '{gap}'"


def test_the_notes_link_every_release_artefact() -> None:
    text = _notes()
    for link in (
        "SECURITY_AUDIT.md",
        "CLAIMS.md",
        "COMPATIBILITY.md",
        "../../../bench/README.md",
    ):
        assert link in text


def test_the_notes_do_not_claim_verification() -> None:
    text = _notes().lower()
    assert "nothing is verified" in text or "not yet verified" in text
    assert "soc 2 certified" not in text
    assert "production-ready" not in text
