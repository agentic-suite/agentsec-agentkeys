"""Secret-hygiene scanner: find what the agent can read, never print it (M8, WBS 8.1/8.2).

Detection reuses the single source of credential-shape knowledge (`agentkeys.redact.SECRET_CLASSES`).
A finding carries location, class, field, and length — there is deliberately no rendering path for
the matched value, so `scan` cannot leak by accident.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, replace
from pathlib import Path

from agentkeys.redact import SECRET_CLASSES

__all__ = ["Finding", "ScanReport", "iter_candidates", "render_report", "scan"]

_MAX_BYTES = 1 << 20
_SCAN_SUFFIXES = {".json", ".toml", ".yaml", ".yml", ".sh", ".bash", ".zsh", ".pem", ".key"}
_SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", ".mypy_cache", ".ruff_cache"}

_ASSIGNMENT = re.compile(r"(?:^|\s)(?:export\s+)?([A-Za-z_][A-Za-z0-9_.-]*)\s*=\s*$")
_JSON_KEY = re.compile(r'"([^"]+)"\s*:\s*"\s*$')
_PRIVATE_KEY = next(pattern for klass, pattern in SECRET_CLASSES if klass == "private-key")


@dataclass(frozen=True)
class _Candidate:
    """An internal hit that still holds the value; it is never rendered or returned."""

    path: str
    line: int
    field: str | None
    class_: str
    value: str

    def __repr__(self) -> str:
        return f"_Candidate(path={self.path!r}, line={self.line}, class_={self.class_!r})"


@dataclass(frozen=True)
class Finding:
    """A masked scan hit: where, what shape, which field — never the value."""

    path: str
    line: int
    field: str | None
    class_: str
    length: int
    broad_reuse: bool = False
    sites: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "line": self.line,
            "field": self.field,
            "class": self.class_,
            "length": self.length,
            "broad_reuse": self.broad_reuse,
            "sites": list(self.sites),
        }


@dataclass(frozen=True)
class ScanReport:
    """The masked result of one scan."""

    root: str
    files_scanned: int
    findings: tuple[Finding, ...]

    @property
    def broad_reuse(self) -> int:
        return sum(1 for finding in self.findings if finding.broad_reuse)

    def to_dict(self) -> dict[str, object]:
        summary: dict[str, int] = {}
        for finding in self.findings:
            summary[finding.class_] = summary.get(finding.class_, 0) + 1
        return {
            "root": self.root,
            "files_scanned": self.files_scanned,
            "findings": [finding.to_dict() for finding in self.findings],
            "summary": dict(sorted(summary.items())),
            "broad_reuse": self.broad_reuse,
        }


def _is_scannable(path: Path) -> bool:
    name = path.name
    return name == ".env" or name.endswith(".env") or path.suffix.lower() in _SCAN_SUFFIXES


def _iter_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.parts):
            continue
        if _is_scannable(path):
            files.append(path)
    return files


def _field_for(line: str, start: int) -> str | None:
    prefix = line[:start]
    match = _JSON_KEY.search(prefix) or _ASSIGNMENT.search(prefix)
    return None if match is None else match.group(1)


def _line_candidates(text: str) -> list[tuple[int, int, str, str]]:
    """Non-overlapping `(line, column, class, value)` hits; first matching pattern wins."""
    hits: list[tuple[int, int, str, str]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        spans: list[tuple[int, int]] = []
        for klass, pattern in SECRET_CLASSES:
            for match in pattern.finditer(line):
                start, end = match.span()
                if any(start < used_end and used_start < end for used_start, used_end in spans):
                    continue
                spans.append((start, end))
                hits.append((line_number, start, klass, match.group(0)))
    return hits


def iter_candidates(root: str | Path) -> tuple[list[_Candidate], int]:
    """Raw candidates plus the file count. For `migrate` only — never rendered."""
    root_path = Path(root)
    candidates: list[_Candidate] = []
    files = _iter_files(root_path)
    for path in files:
        try:
            if path.stat().st_size > _MAX_BYTES:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        relative = path.relative_to(root_path).as_posix()
        private_key_lines: set[int] = set()
        for match in _PRIVATE_KEY.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            for offset in range(match.group(0).count("\n") + 1):
                private_key_lines.add(line + offset)
            candidates.append(
                _Candidate(
                    path=relative,
                    line=line,
                    field=None,
                    class_="private-key",
                    value=match.group(0),
                )
            )
        for line_number, column, klass, value in _line_candidates(text):
            if line_number in private_key_lines:
                continue
            if value.startswith(("akref:", "op://")):
                # A reference is the cure, not a finding: never flag our own rewrite.
                continue
            if klass == "env-assignment":
                _key, _sep, assigned = value.partition("=")
                if assigned.startswith(("akref:", "op://")):
                    continue
            line_text = text.splitlines()[line_number - 1]
            candidates.append(
                _Candidate(
                    path=relative,
                    line=line_number,
                    field=_field_for(line_text, column),
                    class_=klass,
                    value=value,
                )
            )
    return candidates, len(files)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scan(root: str | Path) -> ScanReport:
    """Scan a directory; every finding is masked and values are discarded here."""
    root_path = Path(root)
    if not root_path.is_dir():
        raise FileNotFoundError(f"scan root is not a directory: {root_path}")
    candidates, files_scanned = iter_candidates(root_path)

    by_digest: dict[str, list[int]] = {}
    for index, candidate in enumerate(candidates):
        by_digest.setdefault(_digest(candidate.value), []).append(index)

    findings: list[Finding] = []
    for index, candidate in enumerate(candidates):
        group = by_digest[_digest(candidate.value)]
        sites = tuple(
            sorted({f"{candidates[item].path}:{candidates[item].line}" for item in group})
        )
        finding = Finding(
            path=candidate.path,
            line=candidate.line,
            field=candidate.field,
            class_=candidate.class_,
            length=len(candidate.value),
            broad_reuse=len(sites) > 1,
            sites=sites if len(sites) > 1 else (),
        )
        findings.append(replace(finding))
    return ScanReport(root=str(root_path), files_scanned=files_scanned, findings=tuple(findings))


def render_report(report: ScanReport) -> str:
    """The human view: location, class, field, length, broad-reuse — never a value."""
    lines = [
        f"scan {report.root}: {report.files_scanned} files, {len(report.findings)} candidates, "
        f"{report.broad_reuse} broad-reuse"
    ]
    for finding in report.findings:
        field = finding.field or "-"
        flag = "  broad-reuse" if finding.broad_reuse else ""
        lines.append(
            f"{finding.path}:{finding.line}  {finding.class_}  {field}  "
            f"len={finding.length}{flag}"
        )
    return "\n".join(lines)
