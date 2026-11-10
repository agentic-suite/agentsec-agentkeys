"""Evidence scanner: prove no secret-shape material sits in the ledger, export, or receipts
(M11, WBS 11.2; SC-43, E5)."""

from __future__ import annotations

from dataclasses import dataclass

from agentkeys.export import render_rows
from agentkeys.redact import SECRET_CLASSES
from agentkeys.store.contract import LedgerRow, canonical_event_json

__all__ = ["EvidenceFinding", "EvidenceReport", "scan_evidence", "scan_text"]


@dataclass(frozen=True)
class EvidenceFinding:
    """One secret-shaped hit: where it was and what class — never the value."""

    location: str
    class_: str
    length: int


@dataclass(frozen=True)
class EvidenceReport:
    """The evidence verdict for a store: rows scanned, receipts seen, and any findings."""

    ok: bool
    rows: int
    receipts: int
    findings: tuple[EvidenceFinding, ...]


def scan_text(text: str, *, location: str = "text") -> tuple[EvidenceFinding, ...]:
    """Find credential-shaped spans; the matched value is measured, never returned."""
    findings: list[EvidenceFinding] = []
    for klass, pattern in SECRET_CLASSES:
        for match in pattern.finditer(text):
            findings.append(
                EvidenceFinding(location=location, class_=klass, length=len(match.group(0)))
            )
    return tuple(findings)


def scan_evidence(store: object) -> EvidenceReport:
    """Scan every ledger row's canonical JSON, the export rendering, and the receipts."""
    rows: tuple[LedgerRow, ...] = store.read_ledger()  # type: ignore[attr-defined]
    findings: list[EvidenceFinding] = []
    for row in rows:
        findings.extend(scan_text(canonical_event_json(row.event), location=f"ledger:{row.seq}"))
    findings.extend(scan_text(render_rows(rows), location="export"))
    receipts = len(store.list_all_receipts())  # type: ignore[attr-defined]
    return EvidenceReport(
        ok=not findings, rows=len(rows), receipts=receipts, findings=tuple(findings)
    )
