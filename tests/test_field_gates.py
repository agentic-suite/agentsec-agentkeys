"""Deep validation: ungrounded, mismatched, leaky, and untraced results must be rejected."""

from __future__ import annotations

import json
from pathlib import Path

from agentkeys.fieldtest.cli import main
from agentkeys.fieldtest.gates import (
    collect,
    scan_directory,
    trace_check,
    validate_results,
    verify_harness,
)
from agentkeys.fieldtest.registry import load_registry
from agentkeys.fieldtest.trace import build_traceability, trace_findings

REPO = Path(__file__).resolve().parents[1]
CANONICAL = REPO / "docs" / "field-test" / "v0.1.0" / "FIELD_TEST_REPORT.md"


def _write_summary(base: Path, case_id: str, payload: dict[str, object]) -> Path:
    target = base / case_id
    target.mkdir(parents=True)
    (target / "evidence.txt").write_text("evidence\n")
    payload.setdefault("fingerprint", {"platform": "test"})
    payload.setdefault("evidence", {"files": {"evidence.txt": "0" * 64}})
    (target / "summary.json").write_text(json.dumps(payload))
    return target


def _assertion(
    name: str, expected: object, actual: object, *, passed: bool | None = None
) -> dict[str, object]:
    return {
        "name": name,
        "kind": "eq",
        "expected": expected,
        "actual": actual,
        "passed": (expected == actual) if passed is None else passed,
    }


def test_verify_harness_passes_its_own_self_tests() -> None:
    assert verify_harness() == []


def test_an_ungrounded_pass_is_rejected(tmp_path: Path) -> None:
    _write_summary(
        tmp_path,
        "FT-CL-ENV",
        {
            "case": "FT-CL-ENV",
            "pack": "core",
            "class": "P/F",
            "status": "pass",
            "passed": True,
            "detail": "claimed",
            "assertions": [],
            "limitations": [],
        },
    )
    findings = validate_results(tmp_path, cases=load_registry())
    assert any("assertions" in finding.problem for finding in findings)


def test_a_failed_assertion_cannot_be_a_pass(tmp_path: Path) -> None:
    _write_summary(
        tmp_path,
        "FT-CL-ENV",
        {
            "case": "FT-CL-ENV",
            "pack": "core",
            "class": "P/F",
            "status": "pass",
            "passed": True,
            "detail": "claimed",
            "assertions": [
                _assertion("a", 1, 1),
                _assertion("b", 1, 2, passed=True),
            ],
            "limitations": [],
        },
    )
    findings = validate_results(tmp_path, cases=load_registry())
    assert any("not re-derivable" in finding.problem for finding in findings)


def test_a_warn_on_a_blocking_case_is_rejected(tmp_path: Path) -> None:
    _write_summary(
        tmp_path,
        "FT-RK-KILLTIME",
        {
            "case": "FT-RK-KILLTIME",
            "pack": "killtime",
            "class": "P/F",
            "status": "warn",
            "passed": False,
            "detail": "slow",
            "assertions": [_assertion("a", 1, 1), _assertion("b", 2, 2), _assertion("c", 3, 3)],
            "limitations": ["slow box"],
        },
    )
    findings = validate_results(tmp_path, cases=load_registry())
    assert any("blocking case may not WARN" in finding.problem for finding in findings)


def test_a_not_run_on_a_blocking_case_is_rejected(tmp_path: Path) -> None:
    _write_summary(
        tmp_path,
        "FT-AP-EVIDENCE",
        {
            "case": "FT-AP-EVIDENCE",
            "pack": "attack",
            "class": "P/F",
            "status": "not-run",
            "passed": False,
            "detail": "skipped",
            "assertions": [_assertion("a", 1, 1), _assertion("b", 2, 2), _assertion("c", 3, 3)],
            "limitations": ["no docker"],
        },
    )
    findings = validate_results(tmp_path, cases=load_registry())
    assert any("blocking case may not be NOT RUN" in finding.problem for finding in findings)


def test_the_leak_gate_catches_a_secret_shape(tmp_path: Path) -> None:
    target = tmp_path / "FT-CL-ENV"
    target.mkdir()
    (target / "leak.txt").write_text("sk-FAKE000000000000000000000000000000000")
    assert scan_directory(tmp_path)


def test_an_evidence_hash_mismatch_is_rejected(tmp_path: Path) -> None:
    target = _write_summary(
        tmp_path,
        "FT-CL-ENV",
        {
            "case": "FT-CL-ENV",
            "pack": "core",
            "class": "P/F",
            "status": "pass",
            "passed": True,
            "detail": "ok",
            "assertions": [_assertion("a", 1, 1), _assertion("b", 2, 2)],
            "limitations": [],
        },
    )
    (target / "evidence.txt").write_text("tampered\n")
    findings = validate_results(tmp_path, cases=load_registry())
    assert any("hash mismatch" in finding.problem for finding in findings)


def test_collect_counts_verdicts(tmp_path: Path) -> None:
    _write_summary(
        tmp_path,
        "FT-CL-ENV",
        {
            "case": "FT-CL-ENV",
            "pack": "core",
            "class": "P/F",
            "status": "pass",
            "passed": True,
            "detail": "ok",
            "assertions": [_assertion("a", 1, 1), _assertion("b", 2, 2)],
            "limitations": [],
        },
    )
    payload = collect(tmp_path)
    assert payload["total"]["pass"] == 1
    assert payload["packs"]["core"]["pass"] == 1


def test_trace_reports_missing_results_and_report_rows(tmp_path: Path) -> None:
    report = tmp_path / "report.md"
    report.write_text("# report\n\nHAND-MAINTAINED\n")
    cases = load_registry()
    findings = trace_findings(cases, results_dir=tmp_path, report_path=report)
    assert any("no committed result" in finding for finding in findings)
    assert any("no row in the report" in finding for finding in findings)
    assert trace_check(tmp_path, report_path=report, cases=cases)


def test_traceability_marks_every_case_and_status(tmp_path: Path) -> None:
    text = build_traceability(load_registry(), tmp_path, report_path=CANONICAL)
    for case in load_registry():
        assert case.id in text
    assert "missing" in text


def test_the_cli_gates_exit_codes(tmp_path: Path) -> None:
    assert main(["verify-harness"]) == 0
    assert main(["scan", "--path", str(tmp_path)]) == 0
    assert main(["validate", "--results", str(tmp_path)]) == 1  # no results committed
