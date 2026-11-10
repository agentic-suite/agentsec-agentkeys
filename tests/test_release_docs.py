"""15.7 — the public docs must describe the built core, not the plan.

A stale README is a false claim by omission: it says "not yet" about shipped features and "coming soon"
about work that never landed.
"""

from __future__ import annotations

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
README = (REPO / "README.md").read_text(encoding="utf-8")
GAPS = (REPO / "docs" / "explanation" / "honest-gaps.md").read_text(encoding="utf-8")
DEMOS = (REPO / "docs" / "guides" / "demo-scripts.md").read_text(encoding="utf-8")


def test_the_readme_no_longer_calls_m14_future_work() -> None:
    assert "M14/M15 are next" not in README
    assert "and the M14 field test" not in README
    assert "field tests and release (M14/M15)" not in README


def test_the_readme_states_the_release_state() -> None:
    assert "release candidate" in README.lower()
    assert "0.1.0" in README


def test_the_readme_links_the_field_evidence() -> None:
    for link in (
        "docs/field-test/v0.1.0/FIELD_TEST_REPORT.md",
        "bench/README.md",
        "docs/release/v0.1.0/SECURITY_AUDIT.md",
        "docs/release/v0.1.0/CLAIMS.md",
        "docs/release/v0.1.0/COMPATIBILITY.md",
    ):
        assert link in README, f"README does not link {link}"


def test_the_readme_states_the_field_verdicts() -> None:
    assert "71" in README and "3 WARN" in README
    assert "0 FAIL" in README


def test_the_readme_keeps_the_honest_stubs() -> None:
    """`init`, `context-dump` and `scan-usable` really are stubs — do not 'finish' them in prose."""
    assert "context-dump" in README
    assert "scan-usable" in README
    assert "stub" in README.lower()


def test_the_gaps_doc_stops_promising_m14() -> None:
    assert "field re-run at M14" not in GAPS
    assert "M14 owns" not in GAPS
    assert "not field-tested" not in GAPS.lower(), (
        "M14 produced verdicts; the blanket label is stale"
    )


def test_the_gaps_doc_records_the_three_warns() -> None:
    for case in ("FT-CL-FIRST", "FT-HC-CLAUDE", "FT-HC-CURSOR"):
        assert case in GAPS, f"the gap list dropped {case}"


def test_the_gaps_doc_names_the_blocked_signing_step() -> None:
    text = GAPS.lower()
    assert "signing" in text
    assert "blocked" in text


def test_the_demo_scripts_are_marked_with_their_real_status() -> None:
    assert "Demo 1" in DEMOS and "Demo 2" in DEMOS and "Demo 3" in DEMOS
    text = DEMOS.lower()
    assert "field-tested" in text
    # The scripts themselves are not a rehearsed performance; say so rather than implying they are.
    assert "not been rehearsed" in text or "not yet rehearsed" in text


def test_each_demo_names_the_case_that_backs_it() -> None:
    for case in ("FT-RK-KILLTIME", "FT-AP-CONTEXTDUMP", "FT-ST-NOSECRET"):
        assert case in DEMOS, f"demo evidence missing: {case}"
