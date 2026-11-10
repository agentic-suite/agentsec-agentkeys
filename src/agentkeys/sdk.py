"""The embedder control surface: resolve, use, revoke — and no way to read a stored secret
(M2, WBS 2.6).

There is deliberately **no `get_secret()`**: the only token a caller ever sees is the transient
single-use one returned by `resolve`, and it exists only while the issuance is live and unconsumed.
"""

from __future__ import annotations

import uuid
from typing import Any

from agentkeys.contracts.issuance import IssuanceDoc
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.core.resolution import ResolutionCore, ResolvedIssuance, UseResult
from agentkeys.store.contract import LedgerEvent, RevokeResult

__all__ = ["Broker"]


class Broker:
    """The stable out-of-process control surface for hosts embedding agentkeys."""

    def __init__(self, core: ResolutionCore) -> None:
        self._core = core

    def list_references(self) -> tuple[ReferenceDoc, ...]:
        return self._core.list_references()

    def register_reference(
        self, doc: ReferenceDoc, *, created_at: int = 0, created_by: str = "sdk"
    ) -> ReferenceDoc:
        return self._core.registry.register(doc, created_at=created_at, created_by=created_by)

    def resolve(
        self, reference_id: str, *, audience: str, tool: str, session_id: str
    ) -> ResolvedIssuance:
        """Resolve into a bound, single-use issuance; the token is transient."""
        return self._core.resolve(reference_id, audience=audience, tool=tool, session_id=session_id)

    def use(self, issuance_id: str, token: str, *, now: int | None = None) -> UseResult:
        """Consume the token exactly once; a replay is a typed result, not a grant."""
        return self._core.use(issuance_id, token, now=now)

    def get_issuance(self, issuance_id: str) -> IssuanceDoc | None:
        """Issuance metadata only (no secret, no token)."""
        return self._core.get_issuance(issuance_id)

    def revoke(
        self,
        target_id: str,
        *,
        scope: str = "session",
        reason: str,
        requested_by: str,
        requested_at: int,
        session_id: str | None = None,
    ) -> RevokeResult:
        """Revoke unconditionally (never policy-gated); CAS on the session epoch."""
        event = LedgerEvent(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_version="1.0",
            event_name="revoked",
            occurred_at=requested_at,
            monotonic_ms=0,
            session_id=session_id or target_id,
            agent_id=None,
            reference_id=None,
            issuance_id=None,
            binding_json=None,
            ttl_seconds=None,
            principal=requested_by,
            reason=reason,
            severity="high",
        )
        return self._core.store.cas_revoke(
            scope=scope,
            target_id=target_id,
            requested_by=requested_by,
            requested_at=requested_at,
            reason=reason,
            event=event,
        )

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - guard against accidental surface
        raise AttributeError(
            f"Broker has no attribute {name!r}; there is no secret read-out path by design"
        )
