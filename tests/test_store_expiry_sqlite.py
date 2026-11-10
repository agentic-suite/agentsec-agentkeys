"""SQLite driver coverage for the M6 additions: `list_sessions` and CAS expiry."""

from __future__ import annotations

from pathlib import Path

from agentkeys.events import build_event
from agentkeys.store.contract import Session
from agentkeys.store.sqlite import SqliteStore


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        agent_id="a1",
        harness="cli",
        started_at=1,
        ended_at=None,
        status="active",
        revoke_epoch=0,
        principal="op",
    )


def test_list_sessions_is_ordered(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "s.db")
    store.open()
    try:
        store.create_session(_session("s2"))
        store.create_session(_session("s1"))
        assert [session.session_id for session in store.list_sessions()] == ["s1", "s2"]
    finally:
        store.close()


def test_expire_due_transitions_once(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "s.db")
    store.open()
    try:
        store.create_session(_session("s1"))
        first = store.issue(
            reference_id="ref_1",
            session_id="s1",
            agent_id="a1",
            audience="api.github.com",
            tool="gh",
            class_="dev",
            ttl_seconds=60,
            window=1,
            secret_hash="0" * 64,
            single_use=True,
            issued_at=1000,
            provenance_json="{}",
            binding_hash="b1",
            event=build_event("issuance.created", occurred_at=1000, session_id="s1"),
        )
        assert store.expire_due(1000) == ()
        expired = store.expire_due(2000)
        assert [issuance.issuance_id for issuance in expired] == [first.issuance_id]
        assert store.get_issuance(first.issuance_id).status == "expired"  # type: ignore[union-attr]
        assert store.expire_due(2000) == ()
    finally:
        store.close()
