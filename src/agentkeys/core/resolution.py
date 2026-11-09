"""The resolution core: identity-chain order, idempotent mint, single-use use (M2, PRD 18 §3)."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from agentkeys.config import TtlBound
from agentkeys.contracts.issuance import Binding, IssuanceDoc, IssuanceError
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.store.contract import (
    BrokerStore,
    Issuance,
    LedgerEvent,
    require_capabilities,
)

__all__ = ["ResolutionCore", "ResolutionDenied", "ResolvedIssuance", "UseResult", "UseStatus"]

UseStatus = Literal["consumed", "already_consumed", "expired", "rejected", "unknown"]
_USE_STATUSES: dict[str, UseStatus] = {
    "consumed": "consumed",
    "already_consumed": "already_consumed",
    "expired": "expired",
    "unknown": "unknown",
}

_DEFAULT_TTL_SECONDS = 300
_DEFAULT_WINDOW_SECONDS = 60


class ResolutionDenied(Exception):
    """A fail-closed denial with a machine-readable reason (no credential is minted)."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class ResolvedIssuance:
    """An issuance plus the transient single-use token (never durable, never loggable)."""

    issuance: IssuanceDoc
    token: str | None

    def __repr__(self) -> str:
        token = "None" if self.token is None else "<redacted>"
        return f"ResolvedIssuance(issuance_id={self.issuance.issuance_id!r}, token={token})"


@dataclass(frozen=True)
class UseResult:
    """The typed outcome of using a token (never an exception for a replay)."""

    status: UseStatus


class ResolutionCore:
    """Resolves references into bound, single-use issuances through the BrokerStore."""

    def __init__(
        self,
        store: BrokerStore,
        registry: ReferenceRegistry,
        *,
        ttl: Mapping[str, TtlBound],
        bindings: tuple[tuple[str, str, str], ...],
        clock: Callable[[], int],
        window_seconds: int = _DEFAULT_WINDOW_SECONDS,
        ttl_seconds: int = _DEFAULT_TTL_SECONDS,
    ) -> None:
        require_capabilities(store.capabilities(), ("atomic_issue",))
        self.store = store
        self.registry = registry
        self.clock = clock
        self._ttl = ttl
        self._bindings = frozenset(bindings)
        self._window_seconds = window_seconds
        self._ttl_seconds = ttl_seconds
        self._tokens: dict[str, str] = {}

    # ---------------------------------------------------------------- read-only

    def list_references(self) -> tuple[ReferenceDoc, ...]:
        return self.registry.list()

    def get_issuance(self, issuance_id: str) -> IssuanceDoc | None:
        stored = self.store.get_issuance(issuance_id)
        return None if stored is None else _to_doc(stored)

    # ---------------------------------------------------------------- pipeline

    def resolve(
        self, reference_id: str, *, audience: str, tool: str, session_id: str
    ) -> ResolvedIssuance:
        """Run the ordered pipeline; the first failure denies with a reason."""
        session = self.store.get_session(session_id)
        if session is None:
            raise ResolutionDenied(f"unknown-session: {session_id}")
        if session.revoke_epoch > 0:
            raise ResolutionDenied(f"session-revoked: {session_id}")

        doc = self.registry.get(reference_id=reference_id)
        if (doc.reference_id, audience, tool) not in self._bindings:
            raise ResolutionDenied(f"binding-not-allowed: {reference_id}/{audience}/{tool}")

        now = self.clock()
        window = now // self._window_seconds
        binding_hash = _binding_hash(doc.reference_id, audience, tool, session_id)

        existing = self.store.find_issuance(binding_hash, window)
        if existing is not None:
            return ResolvedIssuance(
                issuance=_to_doc(existing), token=self._tokens.get(existing.issuance_id)
            )

        token = secrets.token_hex(16)  # 128 bits
        secret_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        event = LedgerEvent(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_version="1.0",
            event_name="issuance.created",
            occurred_at=now,
            monotonic_ms=0,
            session_id=session_id,
            agent_id=session.agent_id,
            reference_id=doc.reference_id,
            issuance_id=None,
            binding_json=f'{{"audience":"{audience}","tool":"{tool}"}}',
            ttl_seconds=self._ttl_seconds,
            principal=session.principal,
            reason=None,
            severity="info",
        )
        stored = self.store.issue(
            reference_id=doc.reference_id,
            session_id=session_id,
            agent_id=session.agent_id,
            audience=audience,
            tool=tool,
            class_=doc.class_,
            ttl_seconds=self._ttl_seconds,
            window=window,
            secret_hash=secret_hash,
            single_use=True,
            issued_at=now,
            provenance_json="{}",
            binding_hash=binding_hash,
            event=event,
        )
        issuance = _to_doc(stored)
        issuance.validate_ttl(self._ttl)  # refuse a misconfigured window, never clamp
        self._tokens[stored.issuance_id] = token
        return ResolvedIssuance(issuance=issuance, token=token)

    def use(self, issuance_id: str, token: str, *, now: int | None = None) -> UseResult:
        """Verify the token by hash, then consume it exactly once."""
        stored = self.store.get_issuance(issuance_id)
        if stored is None:
            return UseResult(status="unknown")
        presented = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(presented, stored.secret_hash):
            return UseResult(status="rejected")
        result = self.store.consume(issuance_id, now=self.clock() if now is None else now)
        status = _USE_STATUSES[result.status]
        if status == "consumed":
            self._tokens.pop(issuance_id, None)
        return UseResult(status=status)


def _binding_hash(reference_id: str, audience: str, tool: str, session_id: str) -> str:
    material = "\x00".join((reference_id, audience, tool, session_id))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _to_doc(stored: Issuance) -> IssuanceDoc:
    """Map a stored issuance to the wire document (no `secret_hash`, no token)."""
    try:
        return IssuanceDoc(
            issuance_id=stored.issuance_id,
            reference_id=stored.reference_id,
            session_id=stored.session_id,
            agent_id=stored.agent_id,
            binding=Binding(audience=stored.audience, tool=stored.tool),
            class_=stored.class_,
            ttl=stored.ttl_seconds,
            issued_at=stored.issued_at,
            expires_at=stored.expires_at,
            provenance=None,
        )
    except IssuanceError as exc:  # pragma: no cover - a corrupt row is a store-integrity issue
        raise ResolutionDenied(f"issued-row-malformed: {exc}") from exc
