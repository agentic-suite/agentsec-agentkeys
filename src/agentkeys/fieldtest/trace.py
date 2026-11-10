"""Traceability: plan scenario → case → requirement/feature/CUJ → committed result → report row."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from agentkeys.fieldtest.guards import marker_present
from agentkeys.fieldtest.models import Case

__all__ = ["MAPPINGS", "build_traceability", "trace_findings"]

#: case id → (requirements, feature, CUJ). Scenario comes from cases.yaml.
MAPPINGS: dict[str, tuple[tuple[str, ...], str, str | None]] = {
    "FT-CL-FIRST": (("R1", "R2", "R5", "R17", "E1", "E7"), "F1", "CUJ-1"),
    "FT-CL-ENV": (("R2", "E7"), "F2", "CUJ-1"),
    "FT-CL-HEADER": (("R2", "E7", "E14"), "F3", "CUJ-12"),
    "FT-CL-EXCHANGE": (("R2", "E7"), "F4", "CUJ-1"),
    "FT-CL-TTL": (("E6",), "F5", None),
    "FT-CL-ROTATE": (("R1", "R5", "E6"), "F7", "CUJ-10"),
    "FT-CL-TWOHARNESS": (("E8",), "F17", "CUJ-12"),
    "FT-BR-AUDIENCE": (("R3", "E3", "E7"), "F5", "CUJ-5"),
    "FT-BR-TOOL": (("R3", "E3", "E7"), "F5", "CUJ-5"),
    "FT-BR-SESSION": (("R3", "E3", "E7"), "F5", "CUJ-5"),
    "FT-BR-STALE": (("R3", "E3", "E7"), "F5", "CUJ-5"),
    "FT-ST-NOSECRET": (("R8", "E7", "E14"), "F12", "CUJ-4"),
    "FT-ST-NOPASSTHRU": (("R8", "E14"), "F12", "CUJ-4"),
    "FT-EV-DOTENV": (("R7", "E10"), "F11", "CUJ-6"),
    "FT-EV-CLOUD": (("R7", "E10"), "F11", "CUJ-6"),
    "FT-EV-KEYCHAIN": (("R7", "E10"), "F11", "CUJ-6"),
    "FT-EV-ENFORCE": (("R7", "E10"), "F11", "CUJ-6"),
    "FT-FC-LOCKED": (("R5", "E4", "E9"), "F8", "CUJ-8"),
    "FT-FC-ABSENT": (("R5", "E4", "E9"), "F8", "CUJ-8"),
    "FT-FC-CONFIG": (("E4",), "F16", "CUJ-8"),
    "FT-FC-STORE": (("E2", "E4"), "F15", "CUJ-8"),
    "FT-FC-SINK": (("E4", "E12"), "F9", "CUJ-9"),
    "FT-FC-CRASH": (("E1", "E2", "E4"), "F15", None),
    "FT-RK-KILLTIME": (("R4", "E3", "E6"), "F6", "CUJ-2"),
    "FT-RK-SCOPE": (("R4",), "F6", "CUJ-2"),
    "FT-RK-INFLIGHT": (("R4", "E3"), "F6", "CUJ-2"),
    "FT-RK-UNKNOWN": (("R4",), "F6", "CUJ-2"),
    "FT-RK-ATTR": (("R4", "R6"), "F6", "CUJ-2"),
    "FT-LA-EXPORT": (("R6", "E12"), "F10", "CUJ-9"),
    "FT-LA-TAMPER": (("R6", "E12"), "F10", "CUJ-9"),
    "FT-LA-NOSECRET": (("E5", "E12"), "F14", "CUJ-9"),
    "FT-LA-EVENT": (("R6", "E12"), "F9", "CUJ-9"),
    "FT-SU-APPROVED": (("R9", "E3", "E9"), "F13", "CUJ-7"),
    "FT-SU-DENIED": (("R9", "E3", "E9"), "F13", "CUJ-7"),
    "FT-HC-CLAUDE": (("E8",), "F17", "CUJ-12"),
    "FT-HC-CURSOR": (("E8",), "F17", "CUJ-12"),
    "FT-HC-GENERIC": (("E1", "E8"), "F20", "CUJ-13"),
    "FT-HC-NOTYET": (("E8",), "F17", "CUJ-14"),
    "FT-AG-OFFLINE": (("R5", "E4", "E12"), "F16", "CUJ-11"),
    "FT-AP-CONTEXTDUMP": (("R1", "E5", "E10"), "F19", "CUJ-3"),
    "FT-AP-TAMPER": (("R1", "E5", "E10"), "F19", "CUJ-3"),
    "FT-AP-WIDEN": (("E7",), "F19", "CUJ-5"),
    "FT-AP-EVIDENCE": (("E5", "E10"), "F19", "CUJ-3"),
    "FT-AP-FLOOD": (("E4", "E10"), "F19", "CUJ-6"),
    "FT-MP-SCANMIGRATE": (("R17",), "F21", "CUJ-1"),
    "FT-OPS-SERVE": (("E2", "E10"), "F15", "CUJ-8"),
    "FT-OPS-BACKUP": (("E11", "E12"), "F15", "CUJ-9"),
    "FT-OPS-RESTORE": (("E11", "E12"), "F15", "CUJ-9"),
    "FT-OPS-MIGRATE": (("E11",), "F15", "CUJ-8"),
    "FT-OPS-DOCTOR": (("E4", "E10"), "F8", "CUJ-8"),
    "FT-OPS-DRILL": (("R4",), "F6", "CUJ-2"),
    "FT-OPS-RETENTION": (("E12",), "F9", "CUJ-9"),
    "FT-NFR-INJECT": (("E7",), "F2", None),
    "FT-NFR-BACKEND": (("R5",), "F7", None),
    "FT-NFR-THROUGHPUT": (("R3",), "F5", None),
    "FT-NFR-COLDSTART": (("E2",), "F15", None),
    "FT-NFR-RESTART": (("E2",), "F15", None),
    "FT-NFR-LEDGER": (("R6",), "F9", None),
    "FT-NFR-RSS": (("E2",), "F15", None),
    "FT-NFR-CLOCK": (("E6",), "F5", None),
    "FT-NFR-PORT": (("E4",), "F16", None),
    "FT-NFR-A11Y": (("E4",), "F16", None),
    "FT-CONF-STANDARDS": (("E13",), "F18", "CUJ-14"),
    "FT-CONF-BACKENDS": (("E9", "E13"), "F18", "CUJ-13"),
    "FT-SC-INREPO": (("E15",), "F18", "CUJ-14"),
    "FT-HONESTY-GAPS": (("E15",), "F18", "CUJ-14"),
    "FT-HONESTY-REPORT": (("E15",), "F18", "CUJ-14"),
    "FT-DK-IMAGE": (("E2", "E15"), "F15", None),
    "FT-DK-COMPOSE": (("E2", "E4"), "F15", None),
    "FT-DK-QUICKSTART": (("R1", "R17"), "F1", "CUJ-1"),
    "FT-DK-BOUNDARY": (("R8", "E10"), "F12", "CUJ-4"),
    "FT-DK-AIRGAP": (("E4", "E12"), "F16", "CUJ-11"),
    "FT-DK-EVIDENCE": (("E5",), "F19", "CUJ-3"),
    "FT-DK-SINGLEWRITER": (("E2",), "F15", None),
}

_REQUIREMENTS = {f"R{i}" for i in range(1, 18)} | {f"E{i}" for i in range(1, 16)}
_FEATURES = {f"F{i}" for i in range(1, 24)}
_CUJS = {f"CUJ-{i}" for i in range(1, 15)}


def build_traceability(
    cases: Iterable[Case], results_dir: str | Path, *, report_path: str | Path
) -> str:
    """Render the plan → case → result → report matrix as markdown."""
    base = Path(results_dir)
    statuses: dict[str, str] = {}
    for path in sorted(base.glob("*/summary.json")):
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
            statuses[str(result["case"])] = str(result["status"])
        except (OSError, json.JSONDecodeError, KeyError):
            continue
    report = Path(report_path)
    report_text = report.read_text(encoding="utf-8") if report.is_file() else ""
    lines = [
        "# Field-test traceability — v0.1.0",
        "",
        "> Generated from `cases.yaml`, committed results, and the hand-maintained report.",
        "> Verdicts in the report are hand-entered; this file only proves every plan case",
        "> has a case, a result, and a row.",
        "",
        "| Case | Plan scenario | Requirements | Feature | CUJ | Result | Report row |",
        "|---|---|---|---|---|---|---|",
    ]
    for case in sorted(cases, key=lambda item: item.id):
        requirements, feature, cuj = MAPPINGS.get(case.id, ((), "", None))
        lines.append(
            f"| {case.id} | {case.scenario or '—'} | {', '.join(requirements) or '—'} "
            f"| {feature or '—'} | {cuj or '—'} | {statuses.get(case.id, 'missing')} "
            f"| {'yes' if case.id in report_text else 'NO'} |"
        )
    return "\n".join(lines) + "\n"


def trace_findings(
    cases: Iterable[Case], *, results_dir: str | Path, report_path: str | Path
) -> list[str]:
    """Every case is mapped, every id is valid, every case has a result and a report row."""
    findings: list[str] = []
    base = Path(results_dir)
    result_ids = {
        json.loads(path.read_text(encoding="utf-8")).get("case")
        for path in base.glob("*/summary.json")
    }
    report = Path(report_path)
    report_text = report.read_text(encoding="utf-8") if report.is_file() else ""
    for case in cases:
        mapping = MAPPINGS.get(case.id)
        if mapping is None:
            findings.append(f"{case.id}: no requirement/feature/CUJ mapping")
            continue
        requirements, feature, cuj = mapping
        bad = [item for item in requirements if item not in _REQUIREMENTS]
        if bad:
            findings.append(f"{case.id}: unknown requirement ids {bad}")
        if feature and feature not in _FEATURES:
            findings.append(f"{case.id}: unknown feature id {feature!r}")
        if cuj and cuj not in _CUJS:
            findings.append(f"{case.id}: unknown CUJ {cuj!r}")
        if case.scenario is not None:
            try:
                number = int(case.scenario.removeprefix("SC-"))
            except ValueError:
                findings.append(f"{case.id}: malformed scenario {case.scenario!r}")
            else:
                if not (1 <= number <= 43 or number == 51):
                    findings.append(f"{case.id}: scenario out of the v0.1.0 scope: {case.scenario}")
        if case.id not in result_ids:
            findings.append(f"{case.id}: no committed result")
        if case.id not in report_text:
            findings.append(f"{case.id}: no row in the report")
    if report.is_file() and not marker_present(report):
        findings.append(f"{report}: missing HAND-MAINTAINED marker")
    return findings
