"""15.6 — the risk register must be re-graded against the shipped build, not left at draft."""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "release" / "v0.1.0" / "RISK_REGISTER.md"
PRD = REPO / "docs" / "prd" / "08-risks.md"


def _doc() -> str:
    return DOC.read_text(encoding="utf-8")


def test_every_prd_risk_is_re_graded() -> None:
    prd_ids = set(re.findall(r"\*\*(R-\d+)\*\*", PRD.read_text(encoding="utf-8")))
    doc_ids = set(re.findall(r"\*\*(R-\d+)\*\*", _doc()))
    assert prd_ids <= doc_ids, f"not re-graded: {sorted(prd_ids - doc_ids)}"


def test_each_row_states_an_observed_state() -> None:
    text = _doc()
    rows = [line for line in text.splitlines() if line.startswith("| **R-")]
    assert len(rows) >= 12
    allowed = {"unchanged", "reduced", "increased", "closed", "accepted"}
    for line in rows:
        cells = [cell.strip().lower() for cell in line.strip().strip("|").split("|")]
        assert cells[2] in allowed, f"no observed state on: {line[:80]}"


def test_the_new_risks_surfaced_by_the_field_test_are_recorded() -> None:
    text = _doc().lower()
    for new in ("harness trust", "allowlist", "scanner", "single-maintainer"):
        assert new in text, f"missing new risk: {new}"


def test_dismissed_risks_say_why() -> None:
    text = _doc().lower()
    assert "dismissed" in text
    assert "why" in text or "reason" in text


def test_the_register_does_not_rewrite_the_prd() -> None:
    """PRD 08 is the plan of record; this is an addendum."""
    text = _doc()
    assert "addendum" in text.lower()
    assert "08-risks.md" in text
