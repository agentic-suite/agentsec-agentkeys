"""7.2 — the agentwatch event set: one event per transition, versioned, allow-listed."""

from __future__ import annotations

import pytest

from agentkeys.events import (
    EVENT_NAMES,
    EVENT_VERSION,
    EventEmitter,
    EventError,
    build_event,
    validate_event,
)
from agentkeys.store.memory import MemoryStore


def test_the_event_set_is_the_documented_one() -> None:
    assert EVENT_VERSION == "1.0"
    assert {
        "reference-resolved",
        "issuance.created",
        "use",
        "exchange-rejected",
        "step-up-requested",
        "step-up-granted",
        "step-up-denied",
        "evasion-detected",
        "revoked",
        "expired",
        "sink-gap",
    } <= set(EVENT_NAMES)


def test_build_event_fills_the_common_fields_and_severity() -> None:
    event = build_event(
        "revoked",
        occurred_at=1234,
        session_id="s1",
        agent_id="a1",
        principal="alice",
        reason="operator",
    )
    assert event.event_version == EVENT_VERSION
    assert event.severity == "high"
    assert event.event_id.startswith("evt_")
    assert event.occurred_at == 1234
    assert validate_event(event) is event


def test_an_unknown_event_name_is_refused() -> None:
    with pytest.raises(EventError, match="unknown event"):
        build_event("made-up", occurred_at=1)


def test_an_unknown_severity_is_refused() -> None:
    event = build_event("use", occurred_at=1)
    bad = event.__class__(**{**event.__dict__, "severity": "critical"})
    with pytest.raises(EventError, match="severity"):
        validate_event(bad)


def test_an_emitter_writes_one_row_per_transition() -> None:
    store = MemoryStore()
    store.open()
    emitter = EventEmitter(store, clock=lambda: 1000)
    emitter.emit("issuance.created", session_id="s1", agent_id="a1", reference_id="ref_1")
    emitter.emit("use", session_id="s1", agent_id="a1", issuance_id="iss_1")
    rows = store.read_ledger()
    assert [row.event.event_name for row in rows] == ["issuance.created", "use"]
    assert [row.seq for row in rows] == [1, 2]
    assert rows[1].event.occurred_at == 1000


def test_the_emitter_refuses_an_unknown_name() -> None:
    store = MemoryStore()
    store.open()
    with pytest.raises(EventError):
        EventEmitter(store).emit("not-an-event")
    assert store.read_ledger() == ()
