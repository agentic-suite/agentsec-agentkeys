"""Deep validation: re-derive every assertion, verify evidence hashes, scan for secrets, and trace.

A result is not trusted because the runner exited 0. `validate_results` re-reads each committed
`summary.json`, re-derives every assertion, checks the evidence files exist and match their hashes,
and refuses a PASS with weak or missing proof.
"""

from __future__ import annotations

import hashlib
import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentkeys.evidence import scan_text
from agentkeys.fieldtest.guards import GuardError, marker_present
from agentkeys.fieldtest.models import ASSERTION_KINDS, STATUSES

__all__ = [
    "Finding",
    "collect",
    "scan_directory",
    "trace_check",
    "validate_results",
    "verify_harness",
]

_BLOCKING = {
    "FT-RK-KILLTIME",
    "FT-AP-CONTEXTDUMP",
    "FT-AP-TAMPER",
    "FT-AP-EVIDENCE",
    "FT-MP-SCANMIGRATE",
}
_REQUIRED = (
    "case",
    "pack",
    "class",
    "status",
    "passed",
    "detail",
    "assertions",
    "evidence",
    "fingerprint",
    "limitations",
)


@dataclass(frozen=True)
class Finding:
    location: str
    problem: str

    def __str__(self) -> str:
        return f"{self.location}: {self.problem}"


def _result_files(results_dir: Path) -> list[Path]:
    return sorted(results_dir.glob("*/summary.json"))


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_assertions(
    case_id: str, result: dict[str, Any], location: str, *, count_required: bool = True
) -> list[Finding]:
    findings: list[Finding] = []
    assertions = result.get("assertions")
    if not isinstance(assertions, list):
        return [Finding(location, "assertions is not a list")]
    minimum = 3 if case_id in _BLOCKING else 2
    if count_required and len(assertions) < minimum:
        findings.append(
            Finding(
                location,
                f"only {len(assertions)} assertions; "
                f"{'blocking' if case_id in _BLOCKING else 'standard'} case needs "
                f">= {minimum}",
            )
        )
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            findings.append(Finding(location, f"assertion[{index}] is not an object"))
            continue
        missing = {"name", "kind", "expected", "actual", "passed"} - set(assertion)
        if missing:
            findings.append(Finding(location, f"assertion[{index}] missing {sorted(missing)}"))
            continue
        if assertion["kind"] not in ASSERTION_KINDS:
            findings.append(
                Finding(location, f"assertion[{index}] unknown kind {assertion['kind']!r}")
            )
            continue
        if not str(assertion["name"]).strip():
            findings.append(Finding(location, f"assertion[{index}] has no name"))
        derived = _passed(str(assertion["kind"]), assertion["expected"], assertion["actual"])
        if derived != assertion["passed"]:
            findings.append(
                Finding(
                    location,
                    f"assertion[{index}] passed={assertion['passed']} not re-derivable ({derived})",
                )
            )
    return findings


def _passed(kind: str, expected: Any, actual: Any) -> bool:
    if kind == "eq":
        return bool(actual == expected)
    if kind == "contains":
        return str(expected) in str(actual)
    if kind == "absent":
        return str(expected) not in str(actual)
    if kind == "present":
        return bool(actual) == bool(expected) or bool(actual)
    if kind == "true":
        return actual is True
    if kind == "lte":
        return float(actual) <= float(expected)
    if kind == "gte":
        return float(actual) >= float(expected)
    return False


def validate_results(results_dir: str | Path, *, cases: Any = None) -> list[Finding]:
    """Deep-validate every result in a directory; an empty list means every result is honest."""
    base = Path(results_dir)
    findings: list[Finding] = []
    if not base.is_dir():
        return [Finding(str(base), "results directory missing")]
    files = _result_files(base)
    if not files:
        findings.append(Finding(str(base), "no results committed"))
    catalogs = {case.id: case for case in cases} if cases is not None else {}

    for path in files:
        location = str(path)
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(Finding(location, f"unreadable summary.json: {exc}"))
            continue
        missing = set(_REQUIRED) - set(result)
        if missing:
            findings.append(Finding(location, f"missing keys: {sorted(missing)}"))
            continue
        case_id = str(result["case"])
        if result["status"] not in STATUSES:
            findings.append(Finding(location, f"unknown status {result['status']!r}"))
            continue
        catalog = catalogs.get(case_id)
        if catalogs and catalog is None:
            findings.append(Finding(location, f"case id not in cases.yaml: {case_id}"))
            continue
        if catalog is not None:
            for field in ("pack", "class"):
                expected = catalog.pack if field == "pack" else catalog.klass
                if result[field] != expected:
                    findings.append(
                        Finding(location, f"{field}={result[field]!r} != cases.yaml {expected!r}")
                    )
        findings.extend(
            _validate_assertions(
                case_id, result, location, count_required=result["status"] != "not-run"
            )
        )

        if result["status"] == "pass":
            if not result["assertions"]:
                findings.append(Finding(location, "PASS with no assertions"))
            elif not all(assertion.get("passed") for assertion in result["assertions"]):
                findings.append(Finding(location, "PASS with a failed assertion"))
            if result["passed"] is not True:
                findings.append(Finding(location, "PASS but passed is not true"))
            if not str(result["detail"]).strip():
                findings.append(Finding(location, "PASS with no detail"))
        if result["status"] == "warn":
            if not result["limitations"]:
                findings.append(Finding(location, "WARN with no named limitation"))
            if not str(result["class"]).endswith("W"):
                findings.append(Finding(location, "WARN on a class that does not allow it"))
            if case_id in _BLOCKING:
                findings.append(Finding(location, "blocking case may not WARN"))
        if result["status"] == "fail" and not str(result["detail"]).strip():
            findings.append(Finding(location, "FAIL with no detail"))
        if result["status"] == "not-run":
            if not str(result["detail"]).strip():
                findings.append(Finding(location, "NOT RUN with no reason"))
            if case_id in _BLOCKING:
                findings.append(Finding(location, "blocking case may not be NOT RUN"))

        evidence = result.get("evidence") or {}
        files_map = evidence.get("files") if isinstance(evidence, dict) else None
        if result["status"] == "pass":
            if not files_map:
                findings.append(Finding(location, "PASS without evidence files"))
            else:
                for rel, expected_hash in files_map.items():
                    candidate = (path.parent / rel).resolve()
                    if path.parent.resolve() not in candidate.parents:
                        findings.append(
                            Finding(location, f"evidence path escapes the case dir: {rel}")
                        )
                        continue
                    if not candidate.is_file():
                        findings.append(Finding(location, f"evidence file missing: {rel}"))
                        continue
                    if _hash(candidate) != expected_hash:
                        findings.append(Finding(location, f"evidence hash mismatch: {rel}"))
        if not result.get("fingerprint"):
            findings.append(Finding(location, "no environment fingerprint"))
    return findings


def scan_directory(results_dir: str | Path) -> list[Finding]:
    """Leak gate: no credential shape may appear in any committed result."""
    base = Path(results_dir)
    findings: list[Finding] = []
    if not base.is_dir():
        return [Finding(str(base), "results directory missing")]
    for path in sorted(base.rglob("*")):
        if not path.is_file() or path.suffix == ".pyc":
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for hit in scan_text(text, location=str(path)):
            findings.append(Finding(str(path), f"secret shape ({hit.class_})"))
    return findings


def collect(results_dir: str | Path) -> dict[str, Any]:
    """Aggregate verdicts per pack and overall."""
    base = Path(results_dir)
    packs: dict[str, dict[str, int]] = {}
    total = {status: 0 for status in STATUSES}
    rows: list[dict[str, Any]] = []
    for path in _result_files(base):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        status = result.get("status", "fail")
        pack = result.get("pack", "unknown")
        bucket = packs.setdefault(pack, {state: 0 for state in STATUSES})
        if status in bucket:
            bucket[status] += 1
            total[status] += 1
        rows.append({"case": result.get("case"), "pack": pack, "status": status})
    return {"packs": packs, "total": total, "cases": rows}


def trace_check(results_dir: str | Path, *, report_path: str | Path, cases: Any) -> list[Finding]:
    """Full trace: plan cases → committed results → a row in the hand-maintained report."""
    findings: list[Finding] = []
    catalog = {case.id: case for case in cases}
    result_ids = set()
    for path in _result_files(Path(results_dir)):
        try:
            result_ids.add(json.loads(path.read_text(encoding="utf-8"))["case"])
        except (OSError, json.JSONDecodeError, KeyError):
            findings.append(Finding(str(path), "unreadable case id"))
    missing_results = sorted(set(catalog) - result_ids)
    extra_results = sorted(result_ids - set(catalog))
    if missing_results:
        findings.append(Finding("results", f"plan cases without results: {missing_results}"))
    if extra_results:
        findings.append(Finding("results", f"results without a plan case: {extra_results}"))
    report = Path(report_path)
    if not report.is_file():
        return [Finding(str(report), "report missing")]
    if not marker_present(report):
        findings.append(Finding(str(report), "missing HAND-MAINTAINED marker"))
    text = report.read_text(encoding="utf-8")
    for case_id in sorted(catalog):
        if case_id not in text:
            findings.append(Finding(str(report), f"no report row for {case_id}"))
    return findings


def verify_harness() -> list[Finding]:
    """Prove the gates catch bad results: exercise them on a throwaway copy, never the real run."""
    findings: list[Finding] = []

    def case_dir(base: Path, name: str) -> Path:
        path = base / name
        path.mkdir(parents=True)
        (path / "evidence.txt").write_text("evidence\n")
        return path

    def write(path: Path, result: dict[str, Any]) -> None:
        result.setdefault("fingerprint", {"platform": "self-test"})
        result.setdefault("evidence", {"files": {"evidence.txt": _hash(path / "evidence.txt")}})
        result.setdefault("limitations", [])
        result.setdefault("passed", result.get("status") == "pass")
        result.setdefault("detail", "self-test")
        result.setdefault("pack", "core")
        result.setdefault("class", "P/F")
        result.setdefault("scenario", None)
        (path / "summary.json").write_text(json.dumps(result))

    def assertion(name: str, kind: str, expected: Any, actual: Any) -> dict[str, Any]:
        return {
            "name": name,
            "kind": kind,
            "expected": expected,
            "actual": actual,
            "passed": _passed(kind, expected, actual),
        }

    with tempfile.TemporaryDirectory(prefix="ak-verify-") as directory:
        base = Path(directory)
        good = case_dir(base, "FT-CL-ENV")
        write(
            good,
            {
                "case": "FT-CL-ENV",
                "status": "pass",
                "assertions": [assertion("a", "eq", 1, 1), assertion("b", "eq", 2, 2)],
            },
        )
        if validate_results(base):
            findings.append(Finding("verify", "a clean case was rejected"))

        ungrounded = case_dir(base, "FT-CL-HEADER")
        write(ungrounded, {"case": "FT-CL-HEADER", "status": "pass", "assertions": []})
        if not validate_results(base):
            findings.append(Finding("verify", "an ungrounded PASS was accepted"))

        mismatch = case_dir(base, "FT-CL-TTL")
        write(
            mismatch,
            {
                "case": "FT-CL-TTL",
                "status": "pass",
                "assertions": [assertion("a", "eq", 1, 2), assertion("b", "eq", 1, 1)],
            },
        )
        if not validate_results(base):
            findings.append(Finding("verify", "an assertion mismatch was accepted"))

        warn = case_dir(base, "FT-HC-CLAUDE")
        write(
            warn,
            {
                "case": "FT-HC-CLAUDE",
                "status": "warn",
                "class": "P/F|W",
                "assertions": [assertion("a", "eq", 1, 1)],
                "limitations": [],
            },
        )
        if not validate_results(base):
            findings.append(Finding("verify", "a WARN without a limitation was accepted"))

        (base / "FT-CL-ENV" / "leak.txt").write_text("sk-FAKE000000000000000000000000000000000")
        if not scan_directory(base):
            findings.append(Finding("verify", "the leak gate missed a seeded secret"))

        try:
            from agentkeys.fieldtest.guards import assert_results_target

            assert_results_target(base / "FT-CL-ENV", repo_root=base / "repo")
        except GuardError:
            findings.append(Finding("verify", "a safe results path was refused"))

        marked = base / "marked.json"
        marked.write_text("HAND-MAINTAINED")
        try:
            from agentkeys.fieldtest.guards import assert_results_target

            assert_results_target(marked, repo_root=base)
        except GuardError:
            pass
        else:
            findings.append(Finding("verify", "a marked file was not refused"))
    return findings
