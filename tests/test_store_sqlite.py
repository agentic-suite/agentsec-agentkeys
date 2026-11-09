"""1.2 — the SQLite reference driver: WAL, perms, atomic issue, CAS, chain, live reads."""

from __future__ import annotations

import dataclasses
import sqlite3
from pathlib import Path

import pytest

from agentkeys.store import contract as c
from agentkeys.store.sqlite import SqliteStore
from tests.store_fixtures import issue_kwargs, make_event, make_reference, make_session


@pytest.fixture
def store(tmp_path: Path) -> SqliteStore:
    s = SqliteStore(tmp_path / "agentkeys.db")
    s.open()
    yield s
    s.close()


def _seed(store: SqliteStore) -> None:
    store.create_reference(make_reference())
    store.create_session(make_session())
    store.append_event(make_event(event_id="evt_seed", event_name="session.started"))


def test_capabilities_are_declared(store: SqliteStore) -> None:
    flags = store.capabilities()
    assert flags.single_writer is True
    assert flags.durable is True
    assert flags.atomic_issue is True
    assert flags.cluster_safe is False


def test_wal_and_permissions_are_enforced(tmp_path: Path) -> None:
    old_umask = 0o000
    previous = None
    try:
        previous = __import__("os").umask(old_umask)
        target = tmp_path / "nested" / "agentkeys.db"
        s = SqliteStore(target)
        s.open()
        assert target.parent.stat().st_mode & 0o777 == 0o700
        assert target.stat().st_mode & 0o777 == 0o600
        journal = s.pragma("journal_mode")
        assert journal.lower() == "wal"
        assert s.pragma("synchronous").lower() in {"2", "full"}
        s.close()
    finally:
        if previous is not None:
            __import__("os").umask(previous)


def test_reference_is_idempotent_and_conflicts_are_refused(store: SqliteStore) -> None:
    created = store.create_reference(make_reference())
    again = store.create_reference(make_reference())
    assert created == again
    assert store.get_reference("ref_1") == created
    assert store.list_references() == (created,)
    assert store.get_reference("nope") is None
    conflicting = dataclasses.replace(make_reference(), backend="file")
    with pytest.raises(c.StoreError, match="conflict"):
        store.create_reference(conflicting)


def test_session_round_trip(store: SqliteStore) -> None:
    session = store.create_session(make_session())
    assert session == make_session()
    assert store.get_session("s1") == session
    assert store.get_session("nope") is None


def test_issue_writes_binding_issuance_and_ledger_atomically(store: SqliteStore) -> None:
    _seed(store)
    issuance = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    assert issuance.issuance_id.startswith("iss_")
    assert issuance.expires_at == 1060
    assert issuance.status == "live"
    assert store.get_issuance(issuance.issuance_id) == issuance
    assert store.find_issuance("bh_1", 1) == issuance
    rows = store.read_ledger()
    assert [row.seq for row in rows] == [1, 2]
    assert rows[0].prev_hash == c.GENESIS_PREV_HASH
    assert rows[1].prev_hash == rows[0].hash
    assert rows[1].event.issuance_id == issuance.issuance_id
    assert rows[1].hash == c.compute_hash(rows[1].event, rows[0].hash)


def test_reissue_within_the_same_window_is_idempotent(store: SqliteStore) -> None:
    _seed(store)
    first = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    second = store.issue(**issue_kwargs(event_id="evt_retry"))  # type: ignore[arg-type]
    assert first == second
    assert len(store.read_ledger()) == 2  # no extra issuance event
    binding = store.get_binding("bh_1")
    assert binding is not None and binding.issuance_count == 1
    # a different window mints a new issuance
    third = store.issue(**issue_kwargs(window=2, event_id="evt_next"))  # type: ignore[arg-type]
    assert third.issuance_id != first.issuance_id
    assert len(store.read_ledger()) == 3


def test_consume_is_single_use_and_typed(store: SqliteStore) -> None:
    _seed(store)
    issuance = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    assert store.consume(issuance.issuance_id, now=1001).status == "consumed"
    again = store.consume(issuance.issuance_id, now=1002)
    assert again.status == "already_consumed"
    assert again.issuance is not None and again.issuance.consumed_at == 1001
    assert store.consume("iss_missing", now=1002).status == "unknown"


def test_consume_after_expiry_is_expired(store: SqliteStore) -> None:
    _seed(store)
    issuance = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    assert store.consume(issuance.issuance_id, now=2000).status == "expired"
    assert store.consume(issuance.issuance_id, now=2001).status == "expired"


def test_list_live_excludes_expired_and_consumed(store: SqliteStore) -> None:
    _seed(store)
    live = store.issue(  # type: ignore[arg-type]
        **issue_kwargs(binding_hash="bh_live", event_id="evt_live")
    )
    gone = store.issue(  # type: ignore[arg-type]
        **issue_kwargs(binding_hash="bh_gone", event_id="evt_gone")
    )
    store.consume(gone.issuance_id, now=1001)
    assert [i.issuance_id for i in store.list_live(now=1001)] == [live.issuance_id]
    assert store.list_live(now=5000) == ()


def test_cas_revoke_has_exactly_one_winner(store: SqliteStore) -> None:
    _seed(store)
    first = store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op",
        requested_at=1100,
        reason="operator",
        event=make_event(event_id="evt_rev1", event_name="revoked"),
    )
    assert first.winner is True
    assert first.epoch_before == 0 and first.epoch_after == 1
    assert first.revocation.revocation_id.startswith("rev_")
    assert store.get_session("s1") is not None
    assert store.get_session("s1").revoke_epoch == 1  # type: ignore[union-attr]

    second = store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op2",
        requested_at=1101,
        reason="again",
        event=make_event(event_id="evt_rev2", event_name="revoked"),
    )
    assert second.winner is False
    assert second.revocation.revocation_id == first.revocation.revocation_id
    assert store.get_revocation(first.revocation.revocation_id) == first.revocation
    revoke_events = [
        row for row in store.read_ledger() if row.event.event_name == "revoked"
    ]
    assert len(revoke_events) == 1


def test_cas_revoke_unknown_target_is_an_error(store: SqliteStore) -> None:
    with pytest.raises(c.StoreError, match="unknown"):
        store.cas_revoke(
            scope="session",
            target_id="ghost",
            requested_by="op",
            requested_at=1,
            reason="r",
            event=make_event(),
        )


def test_ledger_reads_are_gapless_and_scoped(store: SqliteStore) -> None:
    _seed(store)
    store.create_session(make_session("s2", agent_id="a2"))
    store.append_event(make_event(event_id="evt_a", session_id="s1"))
    store.append_event(make_event(event_id="evt_b", session_id="s2"))
    store.append_event(make_event(event_id="evt_c", session_id=None))
    rows = store.read_ledger()
    assert [row.seq for row in rows] == [1, 2, 3, 4]
    assert [row.event.event_id for row in store.read_ledger(since_seq=2)] == ["evt_b", "evt_c"]
    assert [row.event.event_id for row in store.export_session("s2")] == ["evt_b"]


def test_append_event_mints_increasing_seq(store: SqliteStore) -> None:
    first = store.append_event(make_event(event_id="e1"))
    second = store.append_event(make_event(event_id="e2"))
    assert (first.seq, second.seq) == (1, 2)
    assert second.prev_hash == first.hash


def test_receipts_round_trip(store: SqliteStore) -> None:
    receipt = c.RedactionReceipt(
        receipt_id="rcpt_1",
        subject_id="iss_1",
        field="header.authorization",
        class_="bearer",
        count=1,
        redactor_version="1.0",
        created_at=1000,
    )
    assert store.add_receipt(receipt) == receipt
    assert store.list_receipts("iss_1") == (receipt,)
    assert store.list_receipts("nope") == ()


def test_duplicate_event_id_is_refused(store: SqliteStore) -> None:
    store.append_event(make_event(event_id="dup"))
    with pytest.raises(c.StoreError, match="duplicate"):
        store.append_event(make_event(event_id="dup"))


def test_busy_store_denies(tmp_path: Path) -> None:
    path = tmp_path / "agentkeys.db"
    first = SqliteStore(path, busy_timeout_ms=50)
    first.open()
    second = SqliteStore(path, busy_timeout_ms=50)
    second.open()
    try:
        first.begin_immediate()
        with pytest.raises(c.StoreBusyError):
            second.append_event(make_event(event_id="e_busy"))
    finally:
        first.rollback()
        first.close()
        second.close()


def test_schema_version_is_recorded(store: SqliteStore) -> None:
    connection = sqlite3.connect(store.path)
    try:
        row = connection.execute("SELECT version FROM schema_version").fetchone()
    finally:
        connection.close()
    assert row is not None and row[0] == 1