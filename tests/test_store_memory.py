"""1.3 — the memory driver: the same semantics, no disk."""

from __future__ import annotations

import dataclasses

import pytest

from agentkeys.store import contract as c
from agentkeys.store.memory import MemoryStore
from tests.store_fixtures import issue_kwargs, make_event, make_reference, make_session


@pytest.fixture
def store() -> MemoryStore:
    s = MemoryStore()
    s.open()
    yield s
    s.close()


def _seed(store: MemoryStore) -> None:
    store.create_reference(make_reference())
    store.create_session(make_session())
    store.append_event(make_event(event_id="evt_seed", event_name="session.started"))


def test_capabilities_are_declared_and_not_durable(store: MemoryStore) -> None:
    flags = store.capabilities()
    assert flags.single_writer is True
    assert flags.durable is False
    assert flags.atomic_issue is True
    assert flags.cluster_safe is False


def test_reference_session_and_conflict(store: MemoryStore) -> None:
    assert store.create_reference(make_reference()) == make_reference()
    assert store.get_reference("ref_1") == make_reference()
    assert store.get_reference("nope") is None
    with pytest.raises(c.StoreError, match="conflict"):
        store.create_reference(dataclasses.replace(make_reference(), backend="file"))
    assert store.create_session(make_session()) == make_session()
    assert store.get_session("s1") == make_session()
    assert store.get_session("nope") is None


def test_issue_is_atomic_idempotent_and_chained(store: MemoryStore) -> None:
    _seed(store)
    first = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    assert first.issuance_id.startswith("iss_")
    assert first.expires_at == 1060
    assert store.issue(**issue_kwargs(event_id="evt_retry")) == first  # type: ignore[arg-type]
    binding = store.get_binding("bh_1")
    assert binding is not None and binding.issuance_count == 1
    rows = store.read_ledger()
    assert [row.seq for row in rows] == [1, 2]
    assert rows[1].prev_hash == rows[0].hash
    assert rows[1].hash == c.compute_hash(rows[1].event, rows[0].hash)
    assert rows[1].event.issuance_id == first.issuance_id


def test_consume_is_single_use(store: MemoryStore) -> None:
    _seed(store)
    issuance = store.issue(**issue_kwargs())  # type: ignore[arg-type]
    assert store.consume(issuance.issuance_id, now=1001).status == "consumed"
    assert store.consume(issuance.issuance_id, now=1002).status == "already_consumed"
    assert store.consume("iss_missing", now=1002).status == "unknown"
    assert store.consume(issuance.issuance_id, now=3000).status == "already_consumed"


def test_expiry_and_live_reads(store: MemoryStore) -> None:
    _seed(store)
    live = store.issue(**issue_kwargs(binding_hash="bh_live", event_id="evt_l"))  # type: ignore[arg-type]
    gone = store.issue(**issue_kwargs(binding_hash="bh_gone", event_id="evt_g"))  # type: ignore[arg-type]
    short = store.issue(  # type: ignore[arg-type]
        **issue_kwargs(binding_hash="bh_short", event_id="evt_s", ttl_seconds=1)
    )
    assert store.consume(gone.issuance_id, now=1001).status == "consumed"
    assert store.consume(short.issuance_id, now=1001).status == "expired"
    assert [i.issuance_id for i in store.list_live(now=1001)] == [live.issuance_id]
    assert store.list_live(now=9999) == ()


def test_cas_revoke_single_winner_and_unknown_target(store: MemoryStore) -> None:
    _seed(store)
    first = store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op",
        requested_at=1100,
        reason="operator",
        event=make_event(event_id="evt_r1", event_name="revoked"),
    )
    assert first.winner and first.epoch_after == 1
    second = store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op2",
        requested_at=1101,
        reason="again",
        event=make_event(event_id="evt_r2", event_name="revoked"),
    )
    assert not second.winner
    assert second.revocation == first.revocation
    assert store.get_revocation(first.revocation.revocation_id) == first.revocation
    assert [r.event.event_name for r in store.read_ledger()].count("revoked") == 1
    with pytest.raises(c.StoreError, match="unknown"):
        store.cas_revoke(
            scope="session",
            target_id="ghost",
            requested_by="op",
            requested_at=1,
            reason="r",
            event=make_event(),
        )


def test_ledger_scoping_gaplessness_and_duplicates(store: MemoryStore) -> None:
    _seed(store)
    store.create_session(make_session("s2", agent_id="a2"))
    store.append_event(make_event(event_id="evt_a", session_id="s1"))
    store.append_event(make_event(event_id="evt_b", session_id="s2"))
    assert [r.seq for r in store.read_ledger()] == [1, 2, 3]
    assert [r.event.event_id for r in store.read_ledger(since_seq=1)] == ["evt_a", "evt_b"]
    assert [r.event.event_id for r in store.export_session("s2")] == ["evt_b"]
    with pytest.raises(c.StoreError, match="duplicate"):
        store.append_event(make_event(event_id="evt_a"))


def test_receipts(store: MemoryStore) -> None:
    receipt = c.RedactionReceipt(
        receipt_id="rcpt_1",
        subject_id="iss_1",
        field="f",
        class_="bearer",
        count=1,
        redactor_version="1.0",
        created_at=1,
    )
    assert store.add_receipt(receipt) == receipt
    assert store.list_receipts("iss_1") == (receipt,)
    assert store.list_receipts("nope") == ()


def test_closed_store_refuses() -> None:
    s = MemoryStore()
    with pytest.raises(c.StoreError, match="not open"):
        s.list_references()