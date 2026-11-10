"""7.1/7.4 — the hash chain verifies, and a rewritten/reordered/deleted row is detected."""

from __future__ import annotations

from dataclasses import replace

from agentkeys.events import build_event
from agentkeys.ledger import verify_chain
from agentkeys.store.memory import MemoryStore


def _store_with_events(count: int = 3) -> MemoryStore:
    store = MemoryStore()
    store.open()
    for index in range(count):
        store.append_event(
            build_event(
                "issuance.created",
                occurred_at=1000 + index,
                session_id="s1",
                agent_id="a1",
                reference_id="ref_1",
                issuance_id=f"iss_{index}",
            )
        )
    return store


def test_a_fresh_chain_verifies() -> None:
    store = _store_with_events()
    report = verify_chain(store.read_ledger())
    assert report.intact is True
    assert report.rows == 3
    assert report.first_bad_seq is None
    assert report.gap_seqs == ()


def test_an_empty_ledger_is_intact() -> None:
    store = MemoryStore()
    store.open()
    report = verify_chain(store.read_ledger())
    assert report.intact is True
    assert report.rows == 0


def test_a_rewritten_row_is_detected_at_its_seq() -> None:
    store = _store_with_events()
    rows = list(store.read_ledger())
    rows[1] = replace(rows[1], event=replace(rows[1].event, reason="rewritten"))
    report = verify_chain(tuple(rows))
    assert report.intact is False
    assert report.first_bad_seq == 2
    assert "hash" in (report.reason or "")


def test_a_deleted_row_is_detected_as_a_gap() -> None:
    store = _store_with_events()
    rows = list(store.read_ledger())
    del rows[1]
    report = verify_chain(tuple(rows))
    assert report.intact is False
    assert report.first_bad_seq == 3
    assert report.gap_seqs


def test_a_reordered_chain_is_detected() -> None:
    store = _store_with_events()
    rows = list(store.read_ledger())
    rows[0], rows[1] = rows[1], rows[0]
    report = verify_chain(tuple(rows))
    assert report.intact is False
    assert report.first_bad_seq == 2


def test_a_forged_prev_hash_is_detected() -> None:
    store = _store_with_events()
    rows = list(store.read_ledger())
    rows[2] = replace(rows[2], prev_hash="f" * 64)
    report = verify_chain(tuple(rows))
    assert report.intact is False
    assert report.first_bad_seq == 3


def test_a_duplicate_seq_is_detected() -> None:
    store = _store_with_events()
    rows = list(store.read_ledger())
    rows.insert(1, rows[0])
    report = verify_chain(tuple(rows))
    assert report.intact is False
    assert report.duplicate_seqs == (1,)
