"""7.5 — join keys so an audit joins the ledger to the session trace."""

from __future__ import annotations

from agentkeys.correlation import correlate, join_keys, session_trace
from agentkeys.events import build_event
from agentkeys.store.contract import LedgerRow
from agentkeys.store.memory import MemoryStore


def _rows() -> tuple[LedgerRow, ...]:
    store = MemoryStore()
    store.open()
    store.append_event(
        build_event(
            "issuance.created",
            occurred_at=1000,
            session_id="s1",
            agent_id="a1",
            reference_id="ref_1",
            issuance_id="iss_1",
        )
    )
    store.append_event(
        build_event(
            "use",
            occurred_at=1001,
            session_id="s1",
            agent_id="a1",
            reference_id="ref_1",
            issuance_id="iss_1",
        )
    )
    store.append_event(
        build_event(
            "issuance.created",
            occurred_at=1002,
            session_id="s2",
            agent_id="a2",
            reference_id="ref_2",
            issuance_id="iss_2",
        )
    )
    store.append_event(
        build_event("revoked", occurred_at=1003, session_id="s2", agent_id="a2", principal="alice")
    )
    return store.read_ledger()


def test_join_keys_name_every_correlation_field() -> None:
    rows = _rows()
    keys = join_keys(rows[1])
    assert keys["session_id"] == "s1"
    assert keys["agent_id"] == "a1"
    assert keys["reference_id"] == "ref_1"
    assert keys["issuance_id"] == "iss_1"


def test_correlate_groups_by_session_in_order() -> None:
    joins = {join.session_id: join for join in correlate(_rows())}
    assert set(joins) == {"s1", "s2"}
    assert joins["s1"].transitions == ("issuance.created", "use")
    assert joins["s1"].reference_ids == ("ref_1",)
    assert joins["s1"].issuance_ids == ("iss_1",)
    assert joins["s2"].transitions == ("issuance.created", "revoked")
    assert joins["s2"].agent_id == "a2"


def test_session_trace_selects_one_session() -> None:
    rows = _rows()
    trace = session_trace(rows, "s2")
    assert [row.event.event_name for row in trace] == ["issuance.created", "revoked"]
