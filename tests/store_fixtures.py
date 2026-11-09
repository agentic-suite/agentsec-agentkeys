"""Shared builders for store tests (drivers are interchangeable)."""

from __future__ import annotations

from agentkeys.store import contract as c


def make_event(
    event_id: str = "evt_1",
    event_name: str = "issuance.created",
    *,
    session_id: str | None = "s1",
    issuance_id: str | None = "iss_1",
    reference_id: str | None = "ref_1",
    severity: str = "info",
    occurred_at: int = 1000,
) -> c.LedgerEvent:
    return c.LedgerEvent(
        event_id=event_id,
        event_version="1.0",
        event_name=event_name,
        occurred_at=occurred_at,
        monotonic_ms=5,
        session_id=session_id,
        agent_id="a1",
        reference_id=reference_id,
        issuance_id=issuance_id,
        binding_json="{}",
        ttl_seconds=60,
        principal="op",
        reason=None,
        severity=severity,
    )


def make_reference(
    reference_id: str = "ref_1",
    *,
    backend: str = "keychain",
    path: str = "agentkeys/dev/token",
    class_: str = "dev",
) -> c.Reference:
    return c.Reference(
        reference_id=reference_id,
        akref_version="1.0",
        backend=backend,
        path=path,
        class_=class_,
        scope_hint=None,
        label="dev token",
        created_at=1000,
        created_by="op",
    )


def make_session(
    session_id: str = "s1", *, agent_id: str = "a1", status: str = "active", revoke_epoch: int = 0
) -> c.Session:
    return c.Session(
        session_id=session_id,
        agent_id=agent_id,
        harness="claude-code",
        started_at=900,
        ended_at=None,
        status=status,
        revoke_epoch=revoke_epoch,
        principal="op",
    )


def issue_kwargs(
    *,
    binding_hash: str = "bh_1",
    window: int = 1,
    session_id: str = "s1",
    secret_hash: str = "hash_1",
    issued_at: int = 1000,
    ttl_seconds: int = 60,
    single_use: bool = True,
    event_id: str = "evt_1",
) -> dict[str, object]:
    """Keyword arguments for `BrokerStore.issue` (the store mints the issuance id)."""
    return {
        "reference_id": "ref_1",
        "session_id": session_id,
        "agent_id": "a1",
        "audience": "api.github.com",
        "tool": "gh",
        "class_": "dev",
        "ttl_seconds": ttl_seconds,
        "window": window,
        "secret_hash": secret_hash,
        "single_use": single_use,
        "issued_at": issued_at,
        "provenance_json": "{}",
        "binding_hash": binding_hash,
        "event": make_event(event_id=event_id, issuance_id=None, session_id=session_id),
    }