"""Correlation: join keys that tie the ledger to a session trace (M7, WBS 7.5; R6).

Every row already carries `session_id`, `agent_id`, `reference_id`, and `issuance_id`; this module
exposes them as a stable join surface instead of making an auditor re-derive them.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentkeys.store.contract import LedgerRow

__all__ = ["TraceJoin", "correlate", "join_keys", "session_trace"]


@dataclass(frozen=True)
class TraceJoin:
    """The ordered lifecycle of one session, with its join keys."""

    session_id: str
    agent_id: str | None
    reference_ids: tuple[str, ...]
    issuance_ids: tuple[str, ...]
    transitions: tuple[str, ...]


def join_keys(row: LedgerRow) -> dict[str, str | None]:
    """The four join keys of one ledger row (missing values are `None`, never guessed)."""
    event = row.event
    return {
        "session_id": event.session_id,
        "agent_id": event.agent_id,
        "reference_id": event.reference_id,
        "issuance_id": event.issuance_id,
    }


def _unique(values: list[str]) -> tuple[str, ...]:
    ordered: list[str] = []
    for value in values:
        if value not in ordered:
            ordered.append(value)
    return tuple(ordered)


def correlate(rows: tuple[LedgerRow, ...]) -> tuple[TraceJoin, ...]:
    """Group rows by session, preserving `seq` order within each session."""
    sessions: dict[str, list[LedgerRow]] = {}
    for row in rows:
        session_id = row.event.session_id
        if session_id is None:
            continue
        sessions.setdefault(session_id, []).append(row)
    joins: list[TraceJoin] = []
    for session_id in sorted(sessions):
        session_rows = sessions[session_id]
        joins.append(
            TraceJoin(
                session_id=session_id,
                agent_id=next(
                    (row.event.agent_id for row in session_rows if row.event.agent_id), None
                ),
                reference_ids=_unique(
                    [row.event.reference_id for row in session_rows if row.event.reference_id]
                ),
                issuance_ids=_unique(
                    [row.event.issuance_id for row in session_rows if row.event.issuance_id]
                ),
                transitions=tuple(row.event.event_name for row in session_rows),
            )
        )
    return tuple(joins)


def session_trace(rows: tuple[LedgerRow, ...], session_id: str) -> tuple[LedgerRow, ...]:
    """The rows for exactly one session, in `seq` order."""
    return tuple(row for row in rows if row.event.session_id == session_id)
