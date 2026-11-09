"""The memory driver: the same semantics as SQLite, ephemeral and lock-protected (M1)."""

from __future__ import annotations

import threading
import uuid
from dataclasses import replace

from agentkeys.store.contract import (
    GENESIS_PREV_HASH,
    Binding,
    CapabilityFlags,
    ConsumeResult,
    Issuance,
    LedgerEvent,
    LedgerRow,
    RedactionReceipt,
    Reference,
    Revocation,
    RevokeResult,
    Session,
    StoreError,
    compute_hash,
)

__all__ = ["MemoryStore"]


class MemoryStore:
    """In-process store with identical semantics to the SQLite driver; no durability."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._open = False
        self._references: dict[str, Reference] = {}
        self._sessions: dict[str, Session] = {}
        self._bindings: dict[str, Binding] = {}
        self._issuances: dict[str, Issuance] = {}
        self._revocations: dict[str, Revocation] = {}
        self._receipts: dict[str, RedactionReceipt] = {}
        self._ledger: list[LedgerRow] = []
        self._event_ids: set[str] = set()

    # ------------------------------------------------------------------ lifecycle

    def capabilities(self) -> CapabilityFlags:
        return CapabilityFlags(
            single_writer=True, durable=False, atomic_issue=True, cluster_safe=False
        )

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def _require_open(self) -> None:
        if not self._open:
            raise StoreError("store is not open")

    # ------------------------------------------------------------------ references

    def create_reference(self, reference: Reference) -> Reference:
        with self._lock:
            self._require_open()
            existing = self._references.get(reference.reference_id)
            if existing is not None:
                if existing != reference:
                    raise StoreError(f"reference conflict: {reference.reference_id}")
                return existing
            self._references[reference.reference_id] = reference
            return reference

    def get_reference(self, reference_id: str) -> Reference | None:
        with self._lock:
            self._require_open()
            return self._references.get(reference_id)

    def list_references(self) -> tuple[Reference, ...]:
        with self._lock:
            self._require_open()
            return tuple(
                self._references[key] for key in sorted(self._references)
            )

    # ------------------------------------------------------------------ sessions

    def create_session(self, session: Session) -> Session:
        with self._lock:
            self._require_open()
            existing = self._sessions.get(session.session_id)
            if existing is not None:
                return existing
            self._sessions[session.session_id] = session
            return session

    def get_session(self, session_id: str) -> Session | None:
        with self._lock:
            self._require_open()
            return self._sessions.get(session_id)

    def get_binding(self, binding_hash: str) -> Binding | None:
        with self._lock:
            self._require_open()
            return self._bindings.get(binding_hash)

    # ------------------------------------------------------------------ issuance

    def issue(
        self,
        *,
        reference_id: str,
        session_id: str,
        agent_id: str,
        audience: str,
        tool: str,
        class_: str,
        ttl_seconds: int,
        window: int,
        secret_hash: str,
        single_use: bool,
        issued_at: int,
        provenance_json: str,
        binding_hash: str,
        event: LedgerEvent,
    ) -> Issuance:
        with self._lock:
            self._require_open()
            for issuance in self._issuances.values():
                if issuance.binding_hash == binding_hash and issuance.window == window:
                    return issuance
            issuance_id = f"iss_{uuid.uuid4().hex}"
            issuance = Issuance(
                issuance_id=issuance_id,
                binding_hash=binding_hash,
                window=window,
                reference_id=reference_id,
                session_id=session_id,
                agent_id=agent_id,
                audience=audience,
                tool=tool,
                class_=class_,
                ttl_seconds=ttl_seconds,
                issued_at=issued_at,
                expires_at=issued_at + ttl_seconds,
                secret_hash=secret_hash,
                single_use=single_use,
                consumed_at=None,
                provenance_json=provenance_json,
                status="live",
            )
            binding = self._bindings.get(binding_hash)
            if binding is None:
                self._bindings[binding_hash] = Binding(
                    binding_hash=binding_hash,
                    reference_id=reference_id,
                    audience=audience,
                    tool=tool,
                    session_id=session_id,
                    first_seen_at=issued_at,
                    issuance_count=1,
                )
            else:
                self._bindings[binding_hash] = replace(
                    binding, issuance_count=binding.issuance_count + 1
                )
            self._issuances[issuance_id] = issuance
            self._append_locked(replace(event, issuance_id=issuance_id))
            return issuance

    def get_issuance(self, issuance_id: str) -> Issuance | None:
        with self._lock:
            self._require_open()
            return self._issuances.get(issuance_id)

    def find_issuance(self, binding_hash: str, window: int) -> Issuance | None:
        with self._lock:
            self._require_open()
            for issuance in self._issuances.values():
                if issuance.binding_hash == binding_hash and issuance.window == window:
                    return issuance
            return None

    def consume(self, issuance_id: str, *, now: int) -> ConsumeResult:
        with self._lock:
            self._require_open()
            issuance = self._issuances.get(issuance_id)
            if issuance is None:
                return ConsumeResult(status="unknown", issuance=None)
            if issuance.consumed_at is not None:
                return ConsumeResult(status="already_consumed", issuance=issuance)
            if issuance.expires_at <= now:
                return ConsumeResult(status="expired", issuance=issuance)
            consumed = replace(issuance, consumed_at=now, status="consumed")
            self._issuances[issuance_id] = consumed
            return ConsumeResult(status="consumed", issuance=consumed)

    def list_live(self, now: int) -> tuple[Issuance, ...]:
        with self._lock:
            self._require_open()
            live = [
                issuance
                for issuance in self._issuances.values()
                if issuance.status == "live"
                and issuance.consumed_at is None
                and issuance.expires_at > now
            ]
        return tuple(sorted(live, key=lambda i: (i.issued_at, i.issuance_id)))

    # ------------------------------------------------------------------ revocation

    def cas_revoke(
        self,
        *,
        scope: str,
        target_id: str,
        requested_by: str,
        requested_at: int,
        reason: str,
        event: LedgerEvent,
    ) -> RevokeResult:
        with self._lock:
            self._require_open()
            session = self._sessions.get(target_id)
            if session is None:
                raise StoreError(f"unknown target: {target_id}")
            if session.revoke_epoch > 0:
                for revocation in self._revocations.values():
                    if revocation.scope == scope and revocation.target_id == target_id:
                        return RevokeResult(
                            revocation=revocation,
                            winner=False,
                            epoch_before=session.revoke_epoch,
                            epoch_after=session.revoke_epoch,
                        )
            revocation = Revocation(
                revocation_id=f"rev_{uuid.uuid4().hex}",
                scope=scope,
                target_id=target_id,
                requested_by=requested_by,
                requested_at=requested_at,
                effective_at=requested_at,
                reason=reason,
                epoch_after=session.revoke_epoch + 1,
            )
            self._sessions[target_id] = replace(session, revoke_epoch=session.revoke_epoch + 1)
            self._revocations[revocation.revocation_id] = revocation
            self._append_locked(event)
            return RevokeResult(
                revocation=revocation,
                winner=True,
                epoch_before=session.revoke_epoch,
                epoch_after=session.revoke_epoch + 1,
            )

    def get_revocation(self, revocation_id: str) -> Revocation | None:
        with self._lock:
            self._require_open()
            return self._revocations.get(revocation_id)

    # ------------------------------------------------------------------ ledger

    def append_event(self, event: LedgerEvent) -> LedgerRow:
        with self._lock:
            self._require_open()
            return self._append_locked(event)

    def _append_locked(self, event: LedgerEvent) -> LedgerRow:
        if event.event_id in self._event_ids:
            raise StoreError(f"duplicate event_id: {event.event_id}")
        seq = len(self._ledger) + 1
        prev_hash = self._ledger[-1].hash if self._ledger else GENESIS_PREV_HASH
        row = LedgerRow(
            seq=seq, event=event, prev_hash=prev_hash, hash=compute_hash(event, prev_hash)
        )
        self._ledger.append(row)
        self._event_ids.add(event.event_id)
        return row

    def read_ledger(self, since_seq: int = 0) -> tuple[LedgerRow, ...]:
        with self._lock:
            self._require_open()
            return tuple(row for row in self._ledger if row.seq > since_seq)

    def export_session(self, session_id: str) -> tuple[LedgerRow, ...]:
        with self._lock:
            self._require_open()
            return tuple(row for row in self._ledger if row.event.session_id == session_id)

    # ------------------------------------------------------------------ receipts

    def add_receipt(self, receipt: RedactionReceipt) -> RedactionReceipt:
        with self._lock:
            self._require_open()
            if receipt.receipt_id in self._receipts:
                raise StoreError(f"duplicate receipt_id: {receipt.receipt_id}")
            self._receipts[receipt.receipt_id] = receipt
            return receipt

    def list_receipts(self, subject_id: str) -> tuple[RedactionReceipt, ...]:
        with self._lock:
            self._require_open()
            matches = [
                receipt
                for receipt in self._receipts.values()
                if receipt.subject_id == subject_id
            ]
        return tuple(sorted(matches, key=lambda r: (r.created_at, r.receipt_id)))