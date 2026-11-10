"""The egress-injection contract: one interface, four normative rules (M4, PRD 02 §4).

Rules every driver inherits: the binding is the ceiling; the client's token is never forwarded; the
audience is enforced at the injector; and a driver forgets what it delivered.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import ClassVar

from agentkeys.backends.contract import SecretValue
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.redact import RedactionDraft
from agentkeys.store.contract import LedgerEvent

__all__ = [
    "AudienceMismatch",
    "BaseInjector",
    "Injection",
    "InjectionDenied",
    "InjectionRequest",
    "WideningRefused",
    "rejection_event",
]

_KINDS = ("env", "header", "exchange")


class InjectionDenied(Exception):
    """A fail-closed injection denial; the caller emits it as an `exchange-rejected` event."""

    REASONS: ClassVar[tuple[str, ...]] = (
        "widening-refused",
        "audience-mismatch",
        "expired",
        "token-unavailable",
        "passthrough-stripped",
        "injector-unavailable",
    )

    def __init__(self, reason: str, detail: str = "") -> None:
        if reason not in self.REASONS:
            raise ValueError(f"unknown denial reason: {reason}")
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


class WideningRefused(InjectionDenied):
    """The request asked for more than the binding allows (another tool or a wider scope)."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("widening-refused", detail)


class AudienceMismatch(InjectionDenied):
    """The request audience (or the injector's own) is not the issuance's audience."""

    def __init__(self, detail: str = "") -> None:
        super().__init__("audience-mismatch", detail)


@dataclass(frozen=True)
class InjectionRequest:
    """What the caller is about to do (never a credential the broker must trust)."""

    audience: str
    tool: str
    client_token: str | None = None
    client_headers: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    scope: str | None = None


@dataclass(frozen=True)
class Injection:
    """The applied material. `env`/`headers`/`token` are the only places a credential may appear."""

    kind: str
    audience: str
    secret: SecretValue
    env: Mapping[str, str] | None = None
    headers: Mapping[str, str] | None = None
    token: SecretValue | None = None
    actor: str | None = None
    receipts: tuple[RedactionDraft, ...] = ()
    overwrote_client_credential: bool = False


def rejection_event(
    *,
    issuance_id: str,
    reason: str,
    audience: str | None = None,
    tool: str | None = None,
    occurred_at: int = 0,
) -> LedgerEvent:
    """The `exchange-rejected` evidence for a refused injection attempt."""
    return LedgerEvent(
        event_id=f"evt_{uuid.uuid4().hex}",
        event_version="1.0",
        event_name="exchange-rejected",
        occurred_at=occurred_at,
        monotonic_ms=0,
        session_id=None,
        agent_id=None,
        reference_id=None,
        issuance_id=issuance_id,
        binding_json=None if audience is None else f'{{"audience":"{audience}","tool":"{tool}"}}',
        ttl_seconds=None,
        principal=None,
        reason=reason,
        severity="warn",
    )


class BaseInjector:
    """Shared enforcement; a driver implements `_deliver` only."""

    kind: ClassVar[str] = "unknown"

    def __init__(self, audience: str) -> None:
        if not audience:
            raise InjectionDenied("injector-unavailable", "an injector needs a target audience")
        self._audience = audience
        self._delivered: list[Injection] = []

    def target_audience(self) -> str:
        return self._audience

    def retained(self) -> int:
        """How many injections this driver is currently holding (drivers must reach zero)."""
        return len(self._delivered)

    def forget(self) -> None:
        """Drop everything about the resolution: nothing may stay observable to the agent."""
        self._delivered.clear()

    def _check(
        self, resolved: ResolvedIssuance, request: InjectionRequest, now: int | None
    ) -> None:
        issuance = resolved.issuance
        expected = issuance.binding.audience
        if request.audience != expected or self._audience != expected:
            raise AudienceMismatch(
                "request/injector audience "
                f"{request.audience}/{self._audience} != issuance {expected}"
            )
        if request.tool != issuance.binding.tool:
            raise WideningRefused(f"tool {request.tool} != bound tool {issuance.binding.tool}")
        if request.scope is not None and request.scope not in ("", issuance.binding.tool):
            raise WideningRefused(
                f"scope {request.scope} is wider than the bound tool {issuance.binding.tool}"
            )
        if now is not None and now >= issuance.expires_at:
            raise InjectionDenied("expired", f"issuance expired at {issuance.expires_at}")
        if resolved.token is None:
            raise InjectionDenied(
                "token-unavailable", "the transient token is not available in this process"
            )

    def apply(
        self, resolved: ResolvedIssuance, *, request: InjectionRequest, now: int | None = None
    ) -> Injection:
        """Enforce the shared rules, then deliver through the driver."""
        self._check(resolved, request, now)
        injection = self._deliver(resolved, request)
        if request.client_token is not None:
            if request.client_token in _injection_values(injection):
                raise InjectionDenied("passthrough-stripped", "the client token reached the output")
            injection = replace(injection, overwrote_client_credential=True)
        self._delivered.append(injection)
        return injection

    def _deliver(self, resolved: ResolvedIssuance, request: InjectionRequest) -> Injection:
        raise NotImplementedError


def _injection_values(injection: Injection) -> str:
    parts: list[str] = []
    if injection.env:
        parts.extend(injection.env.values())
    if injection.headers:
        parts.extend(injection.headers.values())
    if injection.token is not None:
        parts.append(injection.token.reveal())
    return "\x00".join(parts)
