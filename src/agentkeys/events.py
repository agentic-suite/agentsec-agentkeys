"""The agentwatch lifecycle event set and emitter (M7, WBS 7.2, PRD 15 §4).

Names, severities, and fields are an allow-list: an unknown event is refused, never emitted on a
guess. The emitter writes through the BrokerStore contract only (append-only ledger).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import replace

from agentkeys.store.contract import BrokerStore, LedgerEvent, LedgerRow

__all__ = [
    "EVENT_NAMES",
    "EVENT_VERSION",
    "SEVERITIES",
    "EventEmitter",
    "EventError",
    "build_event",
    "validate_event",
]

EVENT_VERSION = "1.0"

#: The lifecycle vocabulary — stable within v0.x, additive only (E11).
EVENT_NAMES: tuple[str, ...] = (
    "reference-resolved",
    "issuance.created",
    "use",
    "exchange-rejected",
    "step-up-requested",
    "step-up-granted",
    "step-up-denied",
    "evasion-detected",
    "revoked",
    "expired",
    "sink-gap",
)

SEVERITIES: tuple[str, ...] = ("info", "warn", "high")

_DEFAULT_SEVERITY: dict[str, str] = {
    "exchange-rejected": "warn",
    "step-up-denied": "warn",
    "evasion-detected": "high",
    "revoked": "high",
    "sink-gap": "warn",
}


class EventError(ValueError):
    """An event outside the allow-list (unknown name or severity)."""


def validate_event(event: LedgerEvent) -> LedgerEvent:
    """Refuse an event whose name or severity is outside the allow-list."""
    if event.event_name not in EVENT_NAMES:
        raise EventError(f"unknown event name: {event.event_name!r}")
    if event.severity not in SEVERITIES:
        raise EventError(f"unknown severity: {event.severity!r}")
    if event.event_version != EVENT_VERSION:
        raise EventError(f"unsupported event_version: {event.event_version!r}")
    return event


def build_event(
    event_name: str,
    *,
    occurred_at: int,
    monotonic_ms: int = 0,
    session_id: str | None = None,
    agent_id: str | None = None,
    reference_id: str | None = None,
    issuance_id: str | None = None,
    binding: tuple[str, str] | None = None,
    ttl_seconds: int | None = None,
    principal: str | None = None,
    reason: str | None = None,
    severity: str | None = None,
) -> LedgerEvent:
    """Build a validated lifecycle event; `binding` is `(audience, tool)`."""
    if event_name not in EVENT_NAMES:
        raise EventError(f"unknown event name: {event_name!r}")
    chosen = severity or _DEFAULT_SEVERITY.get(event_name, "info")
    if chosen not in SEVERITIES:
        raise EventError(f"unknown severity: {chosen!r}")
    binding_json = None
    if binding is not None:
        audience, tool = binding
        binding_json = f'{{"audience":"{audience}","tool":"{tool}"}}'
    return LedgerEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        event_version=EVENT_VERSION,
        event_name=event_name,
        occurred_at=occurred_at,
        monotonic_ms=monotonic_ms,
        session_id=session_id,
        agent_id=agent_id,
        reference_id=reference_id,
        issuance_id=issuance_id,
        binding_json=binding_json,
        ttl_seconds=ttl_seconds,
        principal=principal,
        reason=reason,
        severity=chosen,
    )


class EventEmitter:
    """Emits validated lifecycle events into the ledger (the only place they are recorded)."""

    def __init__(
        self,
        store: BrokerStore,
        *,
        clock: Callable[[], int] | None = None,
        monotonic_ms: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock or (lambda: int(time.time()))
        self._monotonic_ms = monotonic_ms or (lambda: time.monotonic_ns() // 1_000_000)

    def build(self, event_name: str, **fields: object) -> LedgerEvent:
        """Build an event stamped with this emitter's clock."""
        return build_event(
            event_name,
            occurred_at=self._clock(),
            monotonic_ms=self._monotonic_ms(),
            **fields,  # type: ignore[arg-type]
        )

    def emit(self, event_name: str, **fields: object) -> LedgerRow:
        """Build and append one event; an unknown name is refused before any write."""
        return self._store.append_event(self.build(event_name, **fields))
