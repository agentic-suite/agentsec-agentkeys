"""4.6 - session binding: one agent identity per session; bindings die with the session (D-17)."""

from __future__ import annotations

import pytest

from agentkeys.core.sessions import SessionBinder, SessionConflict
from agentkeys.store.contract import LedgerEvent, Session
from agentkeys.store.memory import MemoryStore


def _session(session_id: str = "s1", agent_id: str = "a1", revoke_epoch: int = 0) -> Session:
    return Session(
        session_id=session_id,
        agent_id=agent_id,
        harness="claude-code",
        started_at=1,
        ended_at=None,
        status="active",
        revoke_epoch=revoke_epoch,
        principal="op",
    )


def _revoked_event() -> LedgerEvent:
    return LedgerEvent(
        event_id="rev1",
        event_version="1.0",
        event_name="revoked",
        occurred_at=1500,
        monotonic_ms=1,
        session_id="s1",
        agent_id="a1",
        reference_id=None,
        issuance_id=None,
        binding_json=None,
        ttl_seconds=None,
        principal="op",
        reason="operator",
        severity="high",
    )


@pytest.fixture
def store() -> MemoryStore:
    instance = MemoryStore()
    instance.open()
    instance.create_session(_session())
    return instance


@pytest.fixture
def binder(store: MemoryStore) -> SessionBinder:
    return SessionBinder(store)


def test_the_bound_agent_is_returned(binder: SessionBinder) -> None:
    assert binder.bind("s1", "a1").agent_id == "a1"
    assert binder.agent_for("s1") == "a1"


def test_a_second_agent_cannot_claim_the_session(binder: SessionBinder) -> None:
    with pytest.raises(SessionConflict, match="belongs to agent a1"):
        binder.bind("s1", "a2")


def test_a_revoked_session_refuses(store: MemoryStore, binder: SessionBinder) -> None:
    store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op",
        requested_at=1500,
        reason="operator",
        event=_revoked_event(),
    )
    with pytest.raises(SessionConflict, match="session-revoked"):
        binder.bind("s1", "a1")


def test_an_unknown_session_refuses_and_has_no_ambient_identity(binder: SessionBinder) -> None:
    with pytest.raises(SessionConflict, match="unknown-session"):
        binder.bind("nope", "a1")
    assert binder.agent_for("nope") is None


def test_a_new_session_starts_unbound_to_the_previous_agent(
    store: MemoryStore, binder: SessionBinder
) -> None:
    store.create_session(_session("s2", "a2"))
    assert binder.agent_for("s2") == "a2"
    with pytest.raises(SessionConflict):
        binder.bind("s2", "a1")
