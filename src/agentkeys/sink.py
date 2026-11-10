"""agentwatch sink adapter: ship events best-effort, never let a sink outage rewrite truth (M7).

The local ledger is authoritative. A failing sink keeps the unsent buffer and appends exactly one
`sink-gap` event per failure episode (a named gap, never silent loss and never a degraded allow).
"""

from __future__ import annotations

import time
from collections.abc import Callable

from agentkeys.events import build_event
from agentkeys.store.contract import BrokerStore, LedgerEvent, LedgerRow

__all__ = ["SinkAdapter"]

Sink = Callable[[LedgerRow], None]


class SinkAdapter:
    """Append locally, then attempt delivery; record a gap marker when delivery fails."""

    def __init__(
        self,
        store: BrokerStore,
        sink: Sink | None,
        *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._sink = sink
        self._clock = clock or (lambda: int(time.time()))
        self._pending: list[LedgerRow] = []
        self._gapped = False
        self.gap_markers = 0

    def emit(self, event: LedgerEvent) -> LedgerRow:
        """Append the event locally, then try to ship it (a failure is a gap, not a loss)."""
        row = self._store.append_event(event)
        if self._sink is None:
            return row
        self._pending.append(row)
        self.flush()
        return row

    def flush(self) -> int:
        """Ship pending rows in order; return how many were delivered this call."""
        if self._sink is None:
            return 0
        sent = 0
        while self._pending:
            row = self._pending[0]
            try:
                self._sink(row)
            except Exception as exc:  # a sink is external: any failure is a gap, never an allow
                self._mark_gap(row, exc)
                break
            self._pending.pop(0)
            sent += 1
        if sent:
            self._gapped = False
        return sent

    def _mark_gap(self, row: LedgerRow, exc: Exception) -> None:
        if self._gapped:
            return
        self._gapped = True
        self.gap_markers += 1
        self._store.append_event(
            build_event(
                "sink-gap",
                occurred_at=self._clock(),
                session_id=row.event.session_id,
                issuance_id=row.event.issuance_id,
                reason=f"sink-offline: {exc.__class__.__name__}",
                severity="warn",
            )
        )

    def pending(self) -> tuple[LedgerRow, ...]:
        """Rows not yet delivered, in append order (retained across failures)."""
        return tuple(self._pending)
