"""Time correctness: absolute instants plus a non-decreasing wall view (M6, WBS 6.5; E6).

A backwards clock jump must not extend a TTL, and a forwards jump must not resurrect an expired
issuance. `TimeGuard` is the only clock the revoke/expiry paths consult: it floors small
backwards jumps and refuses large ones (fail closed). `ExpirySweeper` CASes `live -> expired` in
the store so exactly one `expired` event is emitted per issuance, ever.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from agentkeys.store.contract import BrokerStore, Issuance, LedgerEvent

__all__ = ["ClockSkewError", "ExpirySweeper", "TimeGuard"]


class ClockSkewError(Exception):
    """The wall clock moved backwards beyond tolerance; the caller must deny, never guess."""


class TimeGuard:
    """A monotonic-floored view of the wall clock, in UTC epoch seconds."""

    def __init__(
        self,
        clock: Callable[[], int] | None = None,
        *,
        skew_tolerance: int = 0,
    ) -> None:
        if skew_tolerance < 0:
            raise ValueError("skew_tolerance must be >= 0")
        self._clock: Callable[[], int] = clock or (lambda: int(time.time()))
        self._skew_tolerance = skew_tolerance
        self._last: int | None = None

    def observe(self, wall: int) -> int:
        """Fold a wall reading into the non-decreasing view; refuse a large backwards jump."""
        if self._last is None:
            self._last = wall
            return wall
        if wall < self._last:
            if self._last - wall <= self._skew_tolerance:
                # Floor at the last observed second: the jump cannot extend a deadline.
                return self._last
            raise ClockSkewError(
                f"wall clock moved backwards by {self._last - wall}s "
                f"(tolerance {self._skew_tolerance}s)"
            )
        self._last = wall
        return wall

    def now(self) -> int:
        """The current instant, never earlier than a previously observed instant."""
        return self.observe(self._clock())

    def deadline(self, issued_at: int, ttl: int) -> int:
        """The absolute expiry instant for a TTL; a non-positive TTL is refused."""
        if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl <= 0:
            raise ValueError(f"ttl must be a positive integer, got {ttl!r}")
        return issued_at + ttl

    def is_expired(self, expires_at: int) -> bool:
        """Expiry is an absolute-instant comparison (no clamp, no extension)."""
        return self.now() >= expires_at


@dataclass(frozen=True)
class ExpirySweeper:
    """Transitions every live, due issuance to `expired` exactly once and records the event."""

    store: BrokerStore
    guard: TimeGuard

    def sweep(self) -> tuple[Issuance, ...]:
        now = self.guard.now()
        expired = self.store.expire_due(now)
        for issuance in expired:
            self.store.append_event(
                LedgerEvent(
                    event_id=f"evt_{uuid.uuid4().hex}",
                    event_version="1.0",
                    event_name="expired",
                    occurred_at=now,
                    monotonic_ms=0,
                    session_id=issuance.session_id,
                    agent_id=issuance.agent_id,
                    reference_id=issuance.reference_id,
                    issuance_id=issuance.issuance_id,
                    binding_json=(f'{{"audience":"{issuance.audience}","tool":"{issuance.tool}"}}'),
                    ttl_seconds=issuance.ttl_seconds,
                    principal=None,
                    reason=None,
                    severity="info",
                )
            )
        return expired
