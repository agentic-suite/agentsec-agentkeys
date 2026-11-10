"""CLI surface, gate rules, registry guards, trace rendering, and runner edges."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from agentkeys.fieldtest import gates, registry
from agentkeys.fieldtest.cases import CASES_PATH, load_cases
from agentkeys.fieldtest.cli import default_results_dir, main, repo_root
from agentkeys.fieldtest.guards import GuardError, marker_present
from agentkeys.fieldtest.models import (
    Assertion,
    Case,
    CaseOutcome,
    CaseResult,
    RunEnv,
    emit,
)
from agentkeys.fieldtest.registry import CasesError, load_registry
from agentkeys.fieldtest.runner import fingerprint, run_all, run_case
from agentkeys.fieldtest.trace import build_traceability, trace_findings

REPO = Path(__file__).resolve().parents[1]


def _case() -> Case:
    return next(case for case in load_registry() if case.id == "FT-BR-AUDIENCE")


def _summary(base: Path, case_id: str, payload: dict[str, object]) -> Path:
    target = base / case_id
    target.mkdir(parents=True, exist_ok=True)
    (target / "e.txt").write_text("evidence\n")
    payload.setdefault("case", case_id)
    payload.setdefault("pack", "core")
    payload.setdefault("class", "P/F")
    payload.setdefault("status", "pass")
    payload.setdefault("passed", True)
    payload.setdefault("detail", "ok")
    payload.setdefault("limitations", [])
    payload.setdefault("fingerprint", {"platform": "t"})
    payload.setdefault("assertions", [])
    payload.setdefault("evidence", {"files": {"e.txt": "0" * 64}})
    (target / "summary.json").write_text(json.dumps(payload))
    return target


# ---------------------------------------------------------------- CLI


def test_cli_fingerprint(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fingerprint"]) == 0
    assert "platform" in json.loads(capsys.readouterr().out)


def test_cli_run_validate_scan_collect(tmp_path: Path) -> None:
    results = tmp_path / "results"
    assert main(["run", "--pack", "binding", "--results", str(results), "--iterations", "1"]) == 0
    assert main(["validate", "--results", str(results)]) == 0
    assert main(["scan", "--path", str(results)]) == 0
    assert main(["collect", "--results", str(results)]) == 0


def test_cli_run_all_and_case_selection(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = tmp_path / "r"
    assert (
        main(["run", "--pack", "binding", "--case", "FT-BR-TOOL", "--results", str(results)]) == 0
    )
    assert json.loads(capsys.readouterr().out)["ran"] == ["FT-BR-TOOL"]


def test_cli_trace_and_build_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    results = tmp_path / "r"
    results.mkdir()
    report = tmp_path / "report.md"
    report.write_text("HAND-MAINTAINED\n# report\n")
    assert main(["trace", "--results", str(results), "--report", str(report)]) == 1
    out = tmp_path / "gen.md"
    assert main(["build-report", "--results", str(results), "--out", str(out)]) == 0
    assert out.is_file()
    assert main(["verify-harness"]) == 0


def test_cli_default_results_dir_is_the_repo_tree() -> None:
    assert default_results_dir() == repo_root() / "field-test" / "v0.1.0" / "results"


def test_cli_guard_error_is_exit_2(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--pack", "binding", "--results", str(REPO / "docs" / "x")]) == 2
    assert "docs" in capsys.readouterr().err


def test_cli_key_error_is_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--pack", "binding", "--case", "NOPE", "--results", str(tmp_path)]) == 2
    assert "NOPE" in capsys.readouterr().err


def test_module_entry_point() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "agentkeys.fieldtest", "fingerprint"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "platform" in completed.stdout


# ---------------------------------------------------------------- gate rules


def test_validate_a_missing_directory_is_a_finding(tmp_path: Path) -> None:
    findings = gates.validate_results(tmp_path / "missing")
    assert findings and "missing" in findings[0].problem


def test_validate_an_unreadable_summary_is_a_finding(tmp_path: Path) -> None:
    target = tmp_path / "FT-BR-AUDIENCE"
    target.mkdir()
    (target / "summary.json").write_text("{not json")
    assert gates.validate_results(tmp_path)


def test_validate_missing_keys_and_unknown_status(tmp_path: Path) -> None:
    target = tmp_path / "FT-BR-AUDIENCE"
    target.mkdir()
    (target / "summary.json").write_text(json.dumps({"case": "FT-BR-AUDIENCE"}))
    assert any("missing keys" in f.problem for f in gates.validate_results(tmp_path))

    base = tmp_path / "b"
    _summary(base, "FT-BR-AUDIENCE", {"status": "maybe"})
    assert any("unknown status" in f.problem for f in gates.validate_results(base))


def test_validate_unknown_case_when_a_catalog_is_supplied(tmp_path: Path) -> None:
    _summary(tmp_path, "FT-UNKNOWN", {})
    findings = gates.validate_results(tmp_path, cases=load_registry())
    assert any("not in cases.yaml" in f.problem for f in findings)


def test_validate_metadata_mismatch(tmp_path: Path) -> None:
    _summary(
        tmp_path,
        "FT-BR-AUDIENCE",
        {
            "pack": "wrong-pack",
            "class": "P/F",
            "assertions": [
                {"name": "a", "kind": "eq", "expected": 1, "actual": 1, "passed": True},
                {"name": "b", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
            ],
        },
    )
    findings = gates.validate_results(tmp_path, cases=load_registry())
    assert any("cases.yaml" in f.problem for f in findings)


def test_validate_assertion_rules(tmp_path: Path) -> None:
    _summary(
        tmp_path,
        "FT-BR-AUDIENCE",
        {
            "assertions": [
                {"name": "a", "kind": "nope", "expected": 1, "actual": 1, "passed": True},
                {"name": "b", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
                {"name": "c", "kind": "eq", "expected": 3, "actual": 3, "passed": True},
            ]
        },
    )
    findings = gates.validate_results(tmp_path)
    assert any("unknown kind" in f.problem for f in findings)

    base = tmp_path / "b"
    _summary(
        base,
        "FT-BR-AUDIENCE",
        {
            "assertions": [
                {"name": "a", "kind": "eq", "expected": 1, "actual": 1, "passed": True},
                {"name": "", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
                {"name": "c", "expected": 3, "actual": 3, "passed": True},
            ]
        },
    )
    findings = gates.validate_results(base)
    assert any("missing" in f.problem for f in findings)
    assert any("no name" in f.problem for f in findings)

    base2 = tmp_path / "c"
    _summary(
        base2,
        "FT-BR-AUDIENCE",
        {
            "assertions": [
                {"name": "a", "kind": "lte", "expected": 5, "actual": 4, "passed": True},
                {"name": "b", "kind": "is-not-a-kind", "expected": 1, "actual": 1, "passed": True},
            ]
        },
    )
    assert gates.validate_results(base2)


def test_validate_honesty_rules(tmp_path: Path) -> None:
    base = tmp_path / "warn"
    _summary(
        base,
        "FT-BR-AUDIENCE",
        {"status": "warn", "class": "P/F", "assertions": [], "limitations": []},
    )
    findings = gates.validate_results(base)
    assert any("WARN" in f.problem for f in findings)

    base2 = tmp_path / "notrun"
    _summary(base2, "FT-BR-AUDIENCE", {"status": "not-run", "detail": "", "assertions": []})
    assert any("NOT RUN" in f.problem for f in gates.validate_results(base2))

    base3 = tmp_path / "fail"
    _summary(base3, "FT-BR-AUDIENCE", {"status": "fail", "detail": ""})
    assert any("FAIL" in f.problem for f in gates.validate_results(base3))


def test_validate_blocking_not_run_is_rejected(tmp_path: Path) -> None:
    _summary(
        tmp_path,
        "FT-RK-KILLTIME",
        {"pack": "killtime", "status": "not-run", "detail": "x", "assertions": []},
    )
    findings = gates.validate_results(tmp_path)
    assert any("blocking" in f.problem for f in findings)


def test_validate_evidence_rules(tmp_path: Path) -> None:
    target = _summary(
        tmp_path,
        "FT-BR-AUDIENCE",
        {
            "assertions": [
                {"name": "a", "kind": "eq", "expected": 1, "actual": 1, "passed": True},
                {"name": "b", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
            ]
        },
    )
    (target / "e.txt").unlink()
    assert any("evidence file missing" in f.problem for f in gates.validate_results(tmp_path))

    base = tmp_path / "esc"
    _summary(
        base,
        "FT-BR-AUDIENCE",
        {
            "evidence": {"files": {"../outside": "0" * 64}},
            "assertions": [
                {"name": "a", "kind": "eq", "expected": 1, "actual": 1, "passed": True},
                {"name": "b", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
            ],
        },
    )
    assert any("escapes" in f.problem for f in gates.validate_results(base))


def test_validate_no_fingerprint_and_no_evidence(tmp_path: Path) -> None:
    _summary(
        tmp_path,
        "FT-BR-AUDIENCE",
        {
            "fingerprint": {},
            "evidence": {},
            "assertions": [
                {"name": "a", "kind": "eq", "expected": 1, "actual": 1, "passed": True},
                {"name": "b", "kind": "eq", "expected": 2, "actual": 2, "passed": True},
            ],
        },
    )
    findings = gates.validate_results(tmp_path)
    assert any("fingerprint" in f.problem for f in findings)
    assert any("evidence files" in f.problem for f in findings)


def test_collect_on_a_missing_directory_is_empty(tmp_path: Path) -> None:
    payload = gates.collect(tmp_path / "missing")
    assert payload["total"]["pass"] == 0
    assert payload["cases"] == []


def test_scan_ignores_binary_and_missing(tmp_path: Path) -> None:
    target = tmp_path / "c"
    target.mkdir()
    (target / "blob.bin").write_bytes(b"\xff\xfe\x00")
    assert gates.scan_directory(target) == []
    assert gates.scan_directory(tmp_path / "missing")


def test_trace_check_green_and_red(tmp_path: Path) -> None:
    cases = [case for case in load_registry() if case.id in {"FT-BR-AUDIENCE", "FT-BR-TOOL"}]
    base = tmp_path / "r"
    _summary(base, "FT-BR-AUDIENCE", {})
    _summary(base, "FT-BR-TOOL", {})
    report = tmp_path / "report.md"
    report.write_text("HAND-MAINTAINED\nFT-BR-AUDIENCE\nFT-BR-TOOL\n")
    assert gates.trace_check(base, report_path=report, cases=cases) == []
    report.write_text("no marker\n")
    assert gates.trace_check(base, report_path=report, cases=cases)


# ---------------------------------------------------------------- trace


def test_build_traceability_marks_statuses(tmp_path: Path) -> None:
    _summary(tmp_path, "FT-BR-AUDIENCE", {"status": "pass"})
    text = build_traceability(load_registry(), tmp_path, report_path=tmp_path / "missing.md")
    assert "FT-BR-AUDIENCE" in text
    assert "pass" in text
    assert "missing" in text


def test_trace_findings_rejects_unknown_ids(tmp_path: Path) -> None:
    bad = Case(
        id="FT-NOPE",
        pack="core",
        scenario="SC-999",
        klass="P/F",
        env=("ci",),
        driver="x",
    )
    findings = trace_findings([bad], results_dir=tmp_path, report_path=tmp_path / "r.md")
    assert any("no requirement" in f for f in findings)

    mapped = Case(
        id="FT-BR-AUDIENCE",
        pack="core",
        scenario="SC-08",
        klass="P/F",
        env=("ci",),
        driver="x",
    )
    findings = trace_findings([mapped], results_dir=tmp_path, report_path=tmp_path / "r.md")
    assert any("no committed result" in f for f in findings)


# ---------------------------------------------------------------- registry


def test_registry_refuses_a_case_without_an_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(registry.EXECUTORS, "FT-BR-AUDIENCE")
    with pytest.raises(CasesError, match="no executor"):
        load_registry()


def test_registry_refuses_an_executor_without_a_case(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(registry.EXECUTORS, "FT-EXTRA", lambda env, tmp: CaseOutcome("pass", "x"))
    with pytest.raises(CasesError, match="no cases.yaml entry"):
        load_registry()


def test_registry_refuses_duplicate_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    cases = load_cases(CASES_PATH)
    monkeypatch.setattr(registry, "load_cases", lambda path=None: (*cases, cases[0]))
    with pytest.raises(CasesError, match="duplicate"):
        load_registry()


# ---------------------------------------------------------------- runner / guards / models


def test_fingerprint_survives_missing_tools(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("no tool")

    monkeypatch.setattr(subprocess, "run", boom)
    payload = fingerprint(tmp_path)
    assert payload["git_sha"] == "unavailable"
    assert payload["docker"] == "unavailable"


def test_run_all_runs_the_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cases = [case for case in load_registry() if case.id == "FT-BR-AUDIENCE"]
    monkeypatch.setattr("agentkeys.fieldtest.runner.load_registry", lambda: cases)
    results = run_all(RunEnv(repo_root=REPO, results_dir=tmp_path / "r", iterations=1))
    assert [result.case.id for result in results] == ["FT-BR-AUDIENCE"]


def test_marker_present_handles_unreadable_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "x.md"
    target.write_text("HAND-MAINTAINED")

    def boom(self: Path, *args: object, **kwargs: object) -> str:
        raise OSError("unreadable")

    monkeypatch.setattr(Path, "read_text", boom)
    assert marker_present(target) is False


def test_assertion_kinds_and_jsonable() -> None:
    assert Assertion("a", "contains", "x", "axb").passed()
    assert Assertion("a", "absent", "z", "axb").passed()
    assert Assertion("a", "present", True, True).passed()
    assert Assertion("a", "true", True, True).passed()
    assert Assertion("a", "lte", 2, 1).passed()
    assert Assertion("a", "gte", 1, 2).passed()
    with pytest.raises(ValueError):
        Assertion("a", "bogus", 1, 1).passed()
    payload = Assertion("a", "eq", {"x": (1, 2)}, {1, 2}).to_dict()
    assert payload["expected"] == {"x": [1, 2]}
    assert payload["actual"] == ["1", "2"]  # sets are stringified and sorted for JSON


def test_emit_without_assertions_is_a_fail() -> None:
    outcome = emit([], detail="nothing")
    assert outcome.status == "fail"
    assert "no assertions" in outcome.detail


def test_case_result_passed_requires_grounded_assertions() -> None:
    case = _case()
    base = CaseResult(
        case=case,
        status="pass",
        detail="ok",
        assertions=[Assertion("a", "eq", 1, 1)],
        evidence={},
        limitations=[],
        started_at="",
        duration_ms=0,
        fingerprint={},
    )
    assert base.passed is True
    assert CaseResult(**{**base.__dict__, "assertions": []}).passed is False
    assert CaseResult(**{**base.__dict__, "status": "warn"}).passed is False


def test_run_case_rejects_a_marked_target(tmp_path: Path) -> None:
    (tmp_path / "FT-BR-AUDIENCE").write_text("HAND-MAINTAINED")
    env = RunEnv(repo_root=REPO, results_dir=tmp_path, iterations=1)
    with pytest.raises(GuardError):
        run_case(_case(), env)
