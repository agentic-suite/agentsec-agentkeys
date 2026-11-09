"""The BrokerStore contract: typed records, capability flags, chain hashing (M1, PRD 15 §5–§6).

The store is the broker's truth. Every core, backend, and CLI path touches state only through the
`BrokerStore` protocol; the six semantics in `docs/design/v0.1.0/store.md` §5 are the contract.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Any, Literal, Protocol

__all__ = [
    "GENESIS_PREV_HASH",
    "Binding",
    "BrokerStore",
    "CapabilityError",
    "CapabilityFlags",
    "ConsumeResult",
    "ConsumeStatus",
    "DriverError",
    "DriverNotFound",
    "Issuance",
    "LedgerEvent",
    "LedgerRow",
    "RedactionReceipt",
    "Reference",
    "RevokeResult",
    "Revocation",
    "Session",
    "StoreBusyError",
    "StoreError",
    "StoreVersionError",
    "canonical_event_json",
    "compute_hash",
    "require_capabilities",
]

#: The all-zero anchor for the first ledger row's `prev_hash`.
GENESIS_PREV_HASH = "0" * 64

ConsumeStatus = Literal["consumed", "already_consumed", "expired", "unknown"]


class StoreError(Exception):
    """Base class for every store failure (all fail closed)."""


class CapabilityError(StoreError):
    """A driver lacks a capability the caller requires; there is no degraded mode."""


class StoreVersionError(StoreError):
    """The store's schema version is newer than this binary supports (refuse loudly)."""


class StoreBusyError(StoreError):
    """Another writer holds the store; the caller denies rather than waiting forever."""


class DriverError(StoreError):
    """A driver could not be loaded or is not conformant enough to admit."""


class DriverNotFound(DriverError):
    """The requested driver name is not registered (a usage error)."""


@dataclass(frozen=True)
class CapabilityFlags:
    """Declared, checkable properties of a driver (PRD 15 §5)."""

    single_writer: bool
    durable: bool
    atomic_issue: bool
    cluster_safe: bool


@dataclass(frozen=True)
class Reference:
    """An opaque, loggable `akref/1.0` pointer. Never a secret (R1, I1)."""

    reference_id: str
    akref_version: str
    backend: str
    path: str
    class_: str
    scope_hint: str | None
    label: str | None
    created_at: int
    created_by: str


@dataclass(frozen=True)
class Session:
    """An agent session; carries the revocation epoch (`revoke_epoch`)."""

    session_id: str
    agent_id: str
    harness: str
    started_at: int
    ended_at: int | None
    status: str
    revoke_epoch: int
    principal: str


@dataclass(frozen=True)
class Binding:
    """The dedupe key for issuance: `(reference, audience, tool, session)`."""

    binding_hash: str
    reference_id: str
    audience: str
    tool: str
    session_id: str
    first_seen_at: int
    issuance_count: int


@dataclass(frozen=True)
class Issuance:
    """A bound, short-lived issuance. Holds `secret_hash` only — never plaintext (I1/I7)."""

    issuance_id: str
    binding_hash: str
    window: int
    reference_id: str
    session_id: str
    agent_id: str
    audience: str
    tool: str
    class_: str
    ttl_seconds: int
    issued_at: int
    expires_at: int
    secret_hash: str
    single_use: bool
    consumed_at: int | None
    provenance_json: str
    status: str


@dataclass(frozen=True)
class Revocation:
    """A compare-and-set revocation of a session/agent/scope (I3; never policy-gated)."""

    revocation_id: str
    scope: str
    target_id: str
    requested_by: str
    requested_at: int
    effective_at: int
    reason: str
    epoch_after: int


@dataclass(frozen=True)
class LedgerEvent:
    """One lifecycle event, in the agentwatch vocabulary (PRD 15 §4)."""

    event_id: str
    event_version: str
    event_name: str
    occurred_at: int
    monotonic_ms: int
    session_id: str | None
    agent_id: str | None
    reference_id: str | None
    issuance_id: str | None
    binding_json: str | None
    ttl_seconds: int | None
    principal: str | None
    reason: str | None
    severity: str


@dataclass(frozen=True)
class LedgerRow:
    """An appended ledger row: its assigned `seq` and chain hashes."""

    seq: int
    event: LedgerEvent
    prev_hash: str
    hash: str


@dataclass(frozen=True)
class RedactionReceipt:
    """A receipt for one masked field (written from M3)."""

    receipt_id: str
    subject_id: str
    field: str
    class_: str
    count: int
    redactor_version: str
    created_at: int


@dataclass(frozen=True)
class ConsumeResult:
    """The outcome of a single-use consume — a typed state, never an exception."""

    status: ConsumeStatus
    issuance: Issuance | None


@dataclass(frozen=True)
class RevokeResult:
    """The outcome of a CAS revoke: the effective revocation and whether this caller won."""

    revocation: Revocation
    winner: bool
    epoch_before: int
    epoch_after: int


def canonical_event_json(event: LedgerEvent) -> str:
    """Deterministic, ordered JSON of an event (the chain's canonical form)."""
    payload: dict[str, Any] = asdict(event)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_hash(event: LedgerEvent, prev_hash: str) -> str:
    """`H(canonical(event) ‖ prev_hash)` — the tamper-evident chain link (PRD 15 §5)."""
    digest = hashlib.sha256()
    digest.update(canonical_event_json(event).encode("utf-8"))
    digest.update(prev_hash.encode("utf-8"))
    return digest.hexdigest()


def require_capabilities(flags: CapabilityFlags, needed: Iterable[str]) -> None:
    """Refuse a driver that lacks a required capability (no degraded mode, I2)."""
    missing = [name for name in needed if not getattr(flags, name, False)]
    if missing:
        raise CapabilityError(
            "store driver lacks required capability: " + ", ".join(sorted(missing))
        )


class BrokerStore(Protocol):
    """The only path to persisted state."""

    def capabilities(self) -> CapabilityFlags: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def create_reference(self, reference: Reference) -> Reference: ...

    def get_reference(self, reference_id: str) -> Reference | None: ...

    def list_references(self) -> tuple[Reference, ...]: ...

    def create_session(self, session: Session) -> Session: ...

    def get_session(self, session_id: str) -> Session | None: ...

    def get_binding(self, binding_hash: str) -> Binding | None: ...

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
    ) -> Issuance: ...

    def get_issuance(self, issuance_id: str) -> Issuance | None: ...

    def find_issuance(self, binding_hash: str, window: int) -> Issuance | None: ...

    def consume(self, issuance_id: str, *, now: int) -> ConsumeResult: ...

    def list_live(self, now: int) -> tuple[Issuance, ...]: ...

    def cas_revoke(
        self,
        *,
        scope: str,
        target_id: str,
        requested_by: str,
        requested_at: int,
        reason: str,
        event: LedgerEvent,
    ) -> RevokeResult: ...

    def get_revocation(self, revocation_id: str) -> Revocation | None: ...

    def append_event(self, event: LedgerEvent) -> LedgerRow: ...

    def read_ledger(self, since_seq: int = 0) -> tuple[LedgerRow, ...]: ...

    def export_session(self, session_id: str) -> tuple[LedgerRow, ...]: ...

    def add_receipt(self, receipt: RedactionReceipt) -> RedactionReceipt: ...

    def list_receipts(self, subject_id: str) -> tuple[RedactionReceipt, ...]: ...