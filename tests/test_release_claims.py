"""15.2 — the claims lint proves we do not use a stronger word than the evidence supports.

Two things are checked, and both must be real:
  1. the **ledger** (`docs/release/v0.1.0/CLAIMS.md`) — every label resolves to a committed field result, and
     no label outranks its evidence;
  2. the **prose** — the vocabulary the ledger allows is the vocabulary the release docs actually use.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.release import claims

REPO = Path(__file__).resolve().parents[1]
RESULTS = REPO / "field-test" / "v0.1.0" / "results"


def _claim(**overrides: object) -> claims.Claim:
    base: dict[str, object] = {
        "text": "revoke kills access in one second",
        "label": "field-tested",
        "evidence": ("FT-RK-KILLTIME",),
        "third_party": False,
        "note": "",
    }
    base.update(overrides)
    return claims.Claim(**base)  # type: ignore[arg-type]


def _index() -> dict[str, str]:
    return {"FT-RK-KILLTIME": "pass", "FT-CL-FIRST": "warn"}


# ---------------------------------------------------------------- labels vs evidence


def test_the_vocabulary_is_ordered_and_closed() -> None:
    assert claims.LADDER == ("documented", "conformance", "field-tested", "verified")
    assert claims.rank("documented") == 0
    assert claims.rank("verified") == 3
    with pytest.raises(ValueError):
        claims.rank("certified")


def test_a_grounded_field_tested_claim_passes() -> None:
    assert claims.lint_claims([_claim()], _index()) == ()


def test_a_claim_with_no_evidence_above_documented_fails() -> None:
    findings = claims.lint_claims([_claim(evidence=())], _index())
    assert findings
    assert "no evidence" in findings[0].problem


def test_a_claim_pointing_at_a_missing_result_fails() -> None:
    findings = claims.lint_claims([_claim(evidence=("FT-NOPE",))], _index())
    assert any("no committed result" in finding.problem for finding in findings)


def test_warn_evidence_cannot_carry_field_tested() -> None:
    """A WARN is a bounded truth; it earns *documented*, not *field-tested*."""
    findings = claims.lint_claims(
        [_claim(evidence=("FT-CL-FIRST",), label="field-tested")], _index()
    )
    assert any("WARN" in finding.problem for finding in findings)


def test_warn_evidence_is_allowed_at_documented_with_a_note() -> None:
    ok = _claim(evidence=("FT-CL-FIRST",), label="documented", note="no fresh-box median")
    assert claims.lint_claims([ok], _index()) == ()

    silent = _claim(evidence=("FT-CL-FIRST",), label="documented", note="")
    assert claims.lint_claims([silent], _index())


def test_nothing_is_verified_without_a_third_party() -> None:
    findings = claims.lint_claims([_claim(label="verified", third_party=False)], _index())
    assert any("third party" in finding.problem for finding in findings)

    reproduced = _claim(label="verified", third_party=True)
    assert claims.lint_claims([reproduced], _index()) == ()


def test_an_unknown_label_is_a_finding_not_a_crash() -> None:
    findings = claims.lint_claims([_claim(label="production-grade")], _index())
    assert findings
    assert "unknown label" in findings[0].problem


def test_the_failing_evidence_is_named() -> None:
    findings = claims.lint_claims([_claim(evidence=("FT-FAILED",))], {"FT-FAILED": "fail"})
    assert any("fail" in finding.problem for finding in findings)
    assert findings[0].claim == "revoke kills access in one second"


# ---------------------------------------------------------------- the ledger file


def test_the_release_ledger_parses_and_lints_green() -> None:
    ledger = claims.load_ledger(REPO / "docs" / "release" / "v0.1.0" / "CLAIMS.md")
    assert len(ledger) >= 10
    assert {claim.label for claim in ledger} <= set(claims.LADDER)

    findings = claims.lint_claims(ledger, claims.results_index(RESULTS))
    assert findings == (), "\n".join(finding.problem for finding in findings)


def test_the_ledger_records_that_nothing_is_verified() -> None:
    ledger = claims.load_ledger(REPO / "docs" / "release" / "v0.1.0" / "CLAIMS.md")
    assert not [claim for claim in ledger if claim.label == "verified"]


# ---------------------------------------------------------------- the prose


def test_a_banned_superlative_in_a_release_doc_is_a_finding() -> None:
    text = "agentkeys is SOC 2 certified and militarily hardened."
    findings = claims.scan_prose({"docs/release/v0.1.0/NOTES.md": text})
    problems = " ".join(finding.problem for finding in findings)
    assert "SOC 2 certified" in problems
    assert "militarily" in problems


def test_honest_usage_and_non_claims_pass() -> None:
    text = (
        "Kill-time is field-tested; nothing is verified yet. "
        "We are not a compliance certification and not certified."
    )
    assert claims.scan_prose({"docs/release/v0.1.0/NOTES.md": text}) == ()


def test_the_release_docs_and_readme_pass_the_prose_lint() -> None:
    findings = claims.scan_prose(claims.public_files(REPO))
    assert findings == (), "\n".join(f"{f.path}: {f.problem}" for f in findings)
