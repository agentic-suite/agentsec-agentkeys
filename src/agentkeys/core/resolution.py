"""The resolution core: identity-chain order, idempotent mint, single-use use (M2, PRD 18 §3)."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from agentkeys.config import TtlBound
from agentkeys.contracts.issuance import Binding, IssuanceDoc, IssuanceError
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.events import build_event
from agentkeys.stepup import PolicyDecision, StepUpDenied, StepUpGate, StepUpRequest
from agentkeys.store.contract import (
    BrokerStore,
    Issuance,
    LedgerEvent,
    Session,
    require_capabilities,
)
from agentkeys.tamper import EnumerationSignal

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
        enumeration: EnumerationSignal | None = None,
        step_up: StepUpGate | None = None,
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
        self._enumeration = enumeration
        self._step_up = step_up

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

        try:
            doc = self.registry.get(reference_id=reference_id)
        except UnknownReference:
            self._note_unknown_reference(reference_id, session)
            raise
        if (doc.reference_id, audience, tool) not in self._bindings:
            raise ResolutionDenied(f"binding-not-allowed: {reference_id}/{audience}/{tool}")

        now = self.clock()
        self.store.append_event(
            build_event(
                "reference-resolved",
                occurred_at=now,
                session_id=session_id,
                agent_id=session.agent_id,
                reference_id=doc.reference_id,
                binding=(audience, tool),
                principal=session.principal,
            )
        )
        window = now // self._window_seconds
        binding_hash = _binding_hash(doc.reference_id, audience, tool, session_id)

        existing = self.store.find_issuance(binding_hash, window)
        if existing is not None:
            return ResolvedIssuance(
                issuance=_to_doc(existing), token=self._tokens.get(existing.issuance_id)
            )

        provenance_json, step_up_decision = self._authorize_step_up(
            doc.reference_id, doc.class_, session, now, audience, tool
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
            provenance_json=provenance_json,
            binding_hash=binding_hash,
            event=event,
        )
        if step_up_decision is not None:
            self.store.append_event(
                build_event(
                    "step-up-granted",
                    occurred_at=self.clock(),
                    session_id=session_id,
                    agent_id=session.agent_id,
                    reference_id=doc.reference_id,
                    issuance_id=stored.issuance_id,
                    binding=(audience, tool),
                    principal=session.principal,
                    reason=step_up_decision.decided_by,
                )
            )
        issuance = _to_doc(stored)
        issuance.validate_ttl(self._ttl)  # refuse a misconfigured window, never clamp
        self._tokens[stored.issuance_id] = token
        return ResolvedIssuance(issuance=issuance, token=token)

    def _authorize_step_up(
        self,
        reference_id: str,
        class_: str,
        session: Session,
        now: int,
        audience: str,
        tool: str,
    ) -> tuple[str, PolicyDecision | None]:
        """Gate a higher-class mint behind a recorded decision; denial mints nothing."""
        if self._step_up is None or not self._step_up.is_gated(class_):
            return ("{}", None)
        request = StepUpRequest(
            reference_id=reference_id,
            class_=class_,
            session_id=session.session_id,
            agent_id=session.agent_id,
            principal=session.principal,
            audience=audience,
            tool=tool,
            requested_at=now,
        )
        self.store.append_event(
            build_event(
                "step-up-requested",
                occurred_at=now,
                session_id=session.session_id,
                agent_id=session.agent_id,
                reference_id=reference_id,
                binding=(audience, tool),
                principal=session.principal,
            )
        )
        try:
            decision = self._step_up.authorize(request)
        except StepUpDenied as exc:
            self.store.append_event(
                build_event(
                    "step-up-denied",
                    occurred_at=self.clock(),
                    session_id=session.session_id,
                    agent_id=session.agent_id,
                    reference_id=reference_id,
                    binding=(audience, tool),
                    principal=session.principal,
                    reason=exc.reason,
                    severity="warn",
                )
            )
            raise ResolutionDenied(f"step-up-denied: {exc.reason}") from exc
        provenance_json = json.dumps(
            {
                "decided_by": decision.decided_by,
                "decision": "allow",
                "source": decision.source,
            },
            sort_keys=True,
        )
        return (provenance_json, decision)

    def _note_unknown_reference(self, reference_id: str, session: Session) -> None:
        """Repeated unknown-reference probes are an evasion-class signal (M9, 9.6)."""
        if self._enumeration is None:
            return
        if self._enumeration.observe(reference_id, session_id=session.session_id):
            self.store.append_event(
                build_event(
                    "evasion-detected",
                    occurred_at=self.clock(),
                    session_id=session.session_id,
                    agent_id=session.agent_id,
                    principal=session.principal,
                    reason="reference-enumeration",
                    severity="high",
                )
            )

    def use(self, issuance_id: str, token: str, *, now: int | None = None) -> UseResult:
        """Verify the token by hash, then consume it exactly once (a revoked session refuses)."""
        stored = self.store.get_issuance(issuance_id)
        if stored is None:
            return UseResult(status="unknown")
        session = self.store.get_session(stored.session_id)
        if session is None or session.revoke_epoch > 0:
            return UseResult(status="rejected")
        presented = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(presented, stored.secret_hash):
            return UseResult(status="rejected")
        result = self.store.consume(issuance_id, now=self.clock() if now is None else now)
        status = _USE_STATUSES[result.status]
        if status == "consumed":
            self._tokens.pop(issuance_id, None)
            self.store.append_event(
                build_event(
                    "use",
                    occurred_at=self.clock() if now is None else now,
                    session_id=stored.session_id,
                    agent_id=stored.agent_id,
                    reference_id=stored.reference_id,
                    issuance_id=issuance_id,
                    binding=(stored.audience, stored.tool),
                    ttl_seconds=stored.ttl_seconds,
                    principal=session.principal,
                )
            )
        return UseResult(status=status)


def _binding_hash(reference_id: str, audience: str, tool: str, session_id: str) -> str:
    material = "\x00".join((reference_id, audience, tool, session_id))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _to_doc(stored: Issuance) -> IssuanceDoc:
    """Map a stored issuance to the wire document (no `secret_hash`, no token)."""
    provenance: dict[str, str] | None = None
    if stored.provenance_json and stored.provenance_json != "{}":
        try:
            raw = json.loads(stored.provenance_json)
        except json.JSONDecodeError:  # pragma: no cover - a corrupt row is a store-integrity issue
            raw = None
        if isinstance(raw, dict):
            provenance = {str(key): str(value) for key, value in raw.items()}
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
            provenance=provenance,
        )
    except IssuanceError as exc:  # pragma: no cover - a corrupt row is a store-integrity issue
        raise ResolutionDenied(f"issued-row-malformed: {exc}") from exc
