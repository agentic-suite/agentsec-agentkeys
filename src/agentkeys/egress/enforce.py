"""Audience enforcement and rejection evidence (M4, WBS 4.5)."""

from __future__ import annotations

from dataclasses import dataclass

from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import (
    InjectionDenied,
    InjectionRequest,
    rejection_event,
)
from agentkeys.store.contract import LedgerEvent

__all__ = ["Decision", "RejectionLog", "check_injection"]


@dataclass(frozen=True)
class Decision:
    """The injector's verdict: allowed, or denied with a machine-readable reason."""

    allowed: bool
    reason: str | None = None


def check_injection(
    resolved: ResolvedIssuance, request: InjectionRequest, injector_audience: str
) -> Decision:
    """Audience is enforced here, at the injector, not asked of the downstream."""
    issuance = resolved.issuance
    if injector_audience != issuance.binding.audience:
        return Decision(allowed=False, reason="audience-mismatch")
    if request.audience != issuance.binding.audience:
        return Decision(allowed=False, reason="audience-mismatch")
    if request.tool != issuance.binding.tool:
        return Decision(allowed=False, reason="widening-refused")
    if resolved.token is None:
        return Decision(allowed=False, reason="token-unavailable")
    return Decision(allowed=True)


class RejectionLog:
    """Accumulates `exchange-rejected` evidence for refused attempts."""

    def __init__(self) -> None:
        self._events: list[LedgerEvent] = []

    def record(
        self,
        *,
        issuance_id: str,
        reason: str,
        audience: str | None = None,
        tool: str | None = None,
        occurred_at: int = 0,
    ) -> LedgerEvent:
        event = rejection_event(
            issuance_id=issuance_id,
            reason=reason,
            audience=audience,
            tool=tool,
            occurred_at=occurred_at,
        )
        self._events.append(event)
        return event

    def record_denial(
        self,
        denial: InjectionDenied,
        *,
        issuance_id: str,
        audience: str | None = None,
        tool: str | None = None,
    ) -> LedgerEvent:
        return self.record(
            issuance_id=issuance_id, reason=denial.reason, audience=audience, tool=tool
        )

    def events(self) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)
