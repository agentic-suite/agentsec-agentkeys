"""15.3 — the compatibility matrix is generated from committed packs, never hand-filled with optimism.

"No 'supported' without a green pack" (PRD 19 §6). The generator is the enforcement: a row's label is
*derived* from the case status, so an optimistic hand edit cannot survive a rebuild.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.release import compat
from agentkeys.release.claims import results_index

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "field-test" / "v0.1.0" / "results"


def test_every_harness_row_declares_its_required_evidence() -> None:
    rows = compat.ROWS
    assert len(rows) >= 6
    ids = {row.id for row in rows}
    assert {"claude-code", "cursor", "copilot"} <= ids
    for row in rows:
        assert row.tier in {1, 2, 3, "platform"}
        assert row.fallback in compat.LABELS


def test_a_green_pack_earns_first_class() -> None:
    row = compat.Row("harness", 1, "probe", ("FT-RK-KILLTIME",), "why")
    derived = compat.derive(row, {"FT-RK-KILLTIME": "pass"})
    assert derived == "first-class"


def test_a_warn_pack_cannot_earn_first_class() -> None:
    row = compat.Row("harness", 1, "probe", ("FT-HC-CLAUDE",), "why")
    derived = compat.derive(row, {"FT-HC-CLAUDE": "warn"})
    assert derived == "documented", "a WARN live leg is wired, not proven — that is *documented*"


def test_a_row_with_no_pack_is_at_most_documented() -> None:
    row = compat.Row("cli", 1, "scope", (), "reason")
    assert compat.derive(row, {}) == "documented"

    not_yet = compat.Row("cli", 1, "scope", ("FT-MISSING",), "reason")
    assert compat.derive(not_yet, {}) == "not yet"


def test_a_failing_pack_earns_nothing() -> None:
    row = compat.Row("harness", 1, "probe", ("FT-X",), "why")
    assert compat.derive(row, {"FT-X": "fail"}) == "not yet"


def test_the_matrix_is_generated_with_no_supported_without_a_green_pack() -> None:
    text = compat.render(compat.ROWS, results_index(RESULTS))
    index = results_index(RESULTS)

    strong = ("supported", "first-class", "first-class recipe")
    for line in text.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        if any(label in cells[2].lower() for label in strong):
            case = next((c for c in cells[3].split() if c.startswith("FT-")), None)
            assert case is not None, f"no evidence for a strong label: {line}"
            assert index.get(case) == "pass", f"{case} is {index.get(case)}, not pass"


def test_the_committed_document_matches_the_generator() -> None:
    """A hand edit that promotes a row must fail the build, not ship."""
    committed = (REPO / "docs" / "release" / "v0.1.0" / "COMPATIBILITY.md").read_text(
        encoding="utf-8"
    )
    expected = compat.render(compat.ROWS, results_index(RESULTS))

    for line in expected.splitlines():
        if line.strip().startswith("|"):
            assert line in committed, f"the committed matrix drifted from the generator: {line}"


def test_the_honest_labels_are_present() -> None:
    text = compat.render(compat.ROWS, results_index(RESULTS))
    assert "not yet" in text
    assert "lower-layer" in text
    assert "Windows" in text


def test_writing_the_document_is_refused_for_the_report() -> None:
    """The generator may only write its own document — never the hand-maintained field report."""
    from agentkeys.release.compat import write_document

    with pytest.raises(ValueError):
        write_document(REPO / "docs" / "field-test" / "v0.1.0" / "FIELD_TEST_REPORT.md", "x")
