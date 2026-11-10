"""Deterministic, secret-free lifecycle export (M7, WBS 7.3; R6, E12, SC-29/SC-31).

The ledger never stores a plaintext secret, so an export cannot contain one; the test scans the
output anyway. Ordering is by `seq`, so a third party diffing two exports sees real transitions.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentkeys.store.contract import BrokerStore, LedgerRow

__all__ = ["ExportResult", "export_reference", "export_session", "render_rows"]

_FILE_MODE = 0o600


@dataclass(frozen=True)
class ExportResult:
    """The rendered timeline and, when written, where it landed."""

    rows: tuple[LedgerRow, ...]
    text: str
    path: Path | None = None


def _row_payload(row: LedgerRow) -> dict[str, Any]:
    event = row.event
    return {
        "seq": row.seq,
        "event": {
            "event_id": event.event_id,
            "event_version": event.event_version,
            "event_name": event.event_name,
            "occurred_at": event.occurred_at,
            "monotonic_ms": event.monotonic_ms,
            "session_id": event.session_id,
            "agent_id": event.agent_id,
            "reference_id": event.reference_id,
            "issuance_id": event.issuance_id,
            "binding_json": event.binding_json,
            "ttl_seconds": event.ttl_seconds,
            "principal": event.principal,
            "reason": event.reason,
            "severity": event.severity,
        },
        "prev_hash": row.prev_hash,
        "hash": row.hash,
    }


def render_rows(rows: tuple[LedgerRow, ...]) -> str:
    """Ordered JSONL: one canonical object per row, no trailing blank line."""
    return "\n".join(
        json.dumps(_row_payload(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        for row in rows
    )


def _write(text: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(text + ("\n" if text else ""))
    os.chmod(out, _FILE_MODE)


def export_session(
    store: BrokerStore, session_id: str, *, out: str | Path | None = None
) -> ExportResult:
    """Export one session's lifecycle, optionally to a `0600` file."""
    rows = store.export_session(session_id)
    text = render_rows(rows)
    target = None if out is None else Path(out)
    if target is not None:
        _write(text, target)
    return ExportResult(rows=rows, text=text, path=target)


def export_reference(
    store: BrokerStore, reference_id: str, *, out: str | Path | None = None
) -> ExportResult:
    """Export every row that names one reference (ordered by `seq`)."""
    rows = tuple(row for row in store.read_ledger() if row.event.reference_id == reference_id)
    text = render_rows(rows)
    target = None if out is None else Path(out)
    if target is not None:
        _write(text, target)
    return ExportResult(rows=rows, text=text, path=target)
