"""Field-test data model: cases, assertions, outcomes, and the run environment (M14)."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "ASSERTION_KINDS",
    "STATUSES",
    "Assertion",
    "Case",
    "CaseOutcome",
    "CaseResult",
    "RunEnv",
]

STATUSES: tuple[str, ...] = ("pass", "fail", "warn", "not-run")
ASSERTION_KINDS: tuple[str, ...] = ("eq", "contains", "absent", "present", "true", "lte", "gte")


@dataclass(frozen=True)
class Assertion:
    """One machine-recheckable assertion. `expected`/`actual` are kept for re-derivation."""

    name: str
    kind: str
    expected: object
    actual: object

    def passed(self) -> bool:
        if self.kind == "eq":
            return self.actual == self.expected
        if self.kind == "contains":
            return str(self.expected) in str(self.actual)
        if self.kind == "absent":
            return str(self.expected) not in str(self.actual)
        if self.kind == "present":
            return bool(self.actual) is bool(self.expected) or bool(self.actual)
        if self.kind == "true":
            return self.actual is True
        if self.kind == "lte":
            return float(self.actual) <= float(self.expected)  # type: ignore[arg-type]
        if self.kind == "gte":
            return float(self.actual) >= float(self.expected)  # type: ignore[arg-type]
        raise ValueError(f"unknown assertion kind: {self.kind!r}")

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "kind": self.kind,
            "expected": _jsonable(self.expected),
            "actual": _jsonable(self.actual),
            "passed": self.passed(),
        }


def _jsonable(value: object) -> object:
    if isinstance(value, (set, frozenset)):
        return sorted(str(item) for item in value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


@dataclass
class CaseOutcome:
    """What a case executor returns before the runner stamps and writes it."""

    status: str
    detail: str
    assertions: list[Assertion] = field(default_factory=list)
    evidence: dict[str, object] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)


Executor = Callable[["RunEnv", Path], CaseOutcome]


@dataclass(frozen=True)
class Case:
    """One frozen field-test case (metadata from cases.yaml, executor from the registry)."""

    id: str
    pack: str
    scenario: str | None
    klass: str
    env: tuple[str, ...]
    driver: str

    @property
    def blocking(self) -> bool:
        return self.id in {
            "FT-RK-KILLTIME",
            "FT-AP-CONTEXTDUMP",
            "FT-AP-TAMPER",
            "FT-AP-EVIDENCE",
            "FT-MP-SCANMIGRATE",
        }


@dataclass(frozen=True)
class RunEnv:
    """Where a run happens and how long it may take."""

    repo_root: Path
    results_dir: Path
    iterations: int = 100
    fresh_box: bool = False
    docker: bool = True
    env: Mapping[str, str] = field(default_factory=dict)


@dataclass
class CaseResult:
    """The committed result for one case: the only thing the gates read."""

    case: Case
    status: str
    detail: str
    assertions: list[Assertion]
    evidence: dict[str, object]
    limitations: list[str]
    started_at: str
    duration_ms: int
    fingerprint: dict[str, object]

    @property
    def passed(self) -> bool:
        return (
            self.status == "pass"
            and bool(self.assertions)
            and all(assertion.passed() for assertion in self.assertions)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "case": self.case.id,
            "pack": self.case.pack,
            "scenario": self.case.scenario,
            "class": self.case.klass,
            "env": list(self.case.env),
            "driver": self.case.driver,
            "status": self.status,
            "passed": self.passed,
            "detail": self.detail,
            "limitations": list(self.limitations),
            "assertions": [assertion.to_dict() for assertion in self.assertions],
            "evidence": self.evidence,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "fingerprint": self.fingerprint,
        }


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def emit(
    assertions: Sequence[tuple[str, str, object, object]],
    *,
    detail: str,
    evidence: dict[str, object] | None = None,
    limitations: list[str] | None = None,
) -> CaseOutcome:
    """Build an outcome from `(name, kind, expected, actual)` tuples; any miss is a `fail`."""
    parsed = [
        Assertion(name, kind, expected, actual) for name, kind, expected, actual in assertions
    ]
    if not parsed:
        return CaseOutcome(
            status="fail",
            detail=f"no assertions: {detail}",
            assertions=[],
            evidence=evidence or {},
            limitations=limitations or [],
        )
    status = "pass" if all(assertion.passed() for assertion in parsed) else "fail"
    return CaseOutcome(
        status=status,
        detail=detail,
        assertions=parsed,
        evidence=evidence or {},
        limitations=limitations or [],
    )
