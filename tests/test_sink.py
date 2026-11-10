"""7.6 — the sink is best-effort; the local ledger stays authoritative with a gap marker."""

from __future__ import annotations

from agentkeys.events import build_event
from agentkeys.ledger import verify_chain
from agentkeys.sink import SinkAdapter
from agentkeys.store.contract import LedgerRow
from agentkeys.store.memory import MemoryStore


class FlakySink:
    def __init__(self) -> None:
        self.fail = True
        self.sent: list[str] = []

    def __call__(self, row: LedgerRow) -> None:
        if self.fail:
            raise OSError("sink offline")
        self.sent.append(row.event.event_id)


def test_a_failing_sink_leaves_the_local_ledger_authoritative() -> None:
    store = MemoryStore()
    store.open()
    sink = FlakySink()
    adapter = SinkAdapter(store, sink, clock=lambda: 1000)

    adapter.emit(build_event("issuance.created", occurred_at=1000, session_id="s1"))

    assert len(adapter.pending()) == 1
    assert adapter.gap_markers == 1
    rows = store.read_ledger()
    assert [row.event.event_name for row in rows] == ["issuance.created", "sink-gap"]
    gap = rows[-1].event
    assert gap.severity == "warn"
    assert "sink-offline" in (gap.reason or "")
    assert verify_chain(rows).intact is True


def test_the_gap_marker_is_emitted_once_per_failure_episode() -> None:
    store = MemoryStore()
    store.open()
    sink = FlakySink()
    adapter = SinkAdapter(store, sink)
    adapter.emit(build_event("issuance.created", occurred_at=1, session_id="s1"))
    adapter.emit(build_event("use", occurred_at=2, session_id="s1"))
    assert adapter.gap_markers == 1
    assert [row.event.event_name for row in store.read_ledger()].count("sink-gap") == 1


def test_a_recovered_sink_drains_the_buffer() -> None:
    store = MemoryStore()
    store.open()
    sink = FlakySink()
    adapter = SinkAdapter(store, sink)
    adapter.emit(build_event("issuance.created", occurred_at=1, session_id="s1"))
    adapter.emit(build_event("use", occurred_at=2, session_id="s1"))

    sink.fail = False
    assert adapter.flush() == 2
    assert adapter.pending() == ()
    assert len(sink.sent) == 2


def test_without_a_sink_nothing_is_buffered() -> None:
    store = MemoryStore()
    store.open()
    adapter = SinkAdapter(store, None)
    adapter.emit(build_event("use", occurred_at=1, session_id="s1"))
    assert adapter.pending() == ()
    assert adapter.gap_markers == 0
    assert len(store.read_ledger()) == 1


def test_flush_retries_and_drains_after_a_gap() -> None:
    store = MemoryStore()
    store.open()
    sink = FlakySink()
    adapter = SinkAdapter(store, sink)
    adapter.emit(build_event("use", occurred_at=1, session_id="s1"))
    assert adapter.flush() == 0
    assert adapter.gap_markers == 1
    assert len(adapter.pending()) == 1

    sink.fail = False
    assert adapter.flush() == 1
    assert adapter.pending() == ()
    assert len(sink.sent) == 1
