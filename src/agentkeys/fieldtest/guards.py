"""Guardrails: the report is hand-maintained; results never live under docs."""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "CANONICAL_REPORT",
    "REFUSED_MARKER",
    "GuardError",
    "assert_results_target",
    "marker_present",
]

REFUSED_MARKER = "HAND-MAINTAINED"

CANONICAL_REPORT = Path("docs/field-test/v0.1.0/FIELD_TEST_REPORT.md")


class GuardError(Exception):
    """A write that would touch a hand-maintained or forbidden path."""


def marker_present(path: str | Path) -> bool:
    """Whether a file carries the hand-maintained marker (checked on the first 4 KiB)."""
    file = Path(path)
    if not file.is_file():
        return False
    try:
        return REFUSED_MARKER in file.read_text(encoding="utf-8", errors="ignore")[:4096]
    except OSError:
        return False


def assert_results_target(path: str | Path, *, repo_root: Path) -> Path:
    """Resolve and vet a results path: never under `docs/`, never over a marked file."""
    resolved = Path(path).resolve()
    docs = (repo_root / "docs").resolve()
    if resolved == docs or docs in resolved.parents:
        raise GuardError(f"refusing to write results under docs/: {resolved}")
    if marker_present(resolved):
        raise GuardError(f"refusing to overwrite a HAND-MAINTAINED file: {resolved}")
    return resolved
