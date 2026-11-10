"""9.5/9.6 — spoofed references, enumeration probes, and an unavailable broker all fail closed."""

from __future__ import annotations

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.store.contract import Session, StoreError
from agentkeys.store.memory import MemoryStore
from agentkeys.tamper import EnumerationSignal

TTL = {"dev": TtlBound(floor=30, ceiling=900)}


def _core(signal: EnumerationSignal | None = None) -> ResolutionCore:
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id="s1",
            agent_id="a1",
            harness="claude-code",
            started_at=1,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )
    ReferenceRegistry(store).register(
        ReferenceDoc(
            reference_id="ref_1",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            label="dev token",
        )
    )
    return ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_1", "api.github.com", "gh"),),
        clock=lambda: 1000,
        enumeration=signal,
    )


def test_a_spoofed_reference_is_denied() -> None:
    core = _core()
    with pytest.raises(UnknownReference):
        core.resolve("ref_invented", audience="api.github.com", tool="gh", session_id="s1")
    assert [row.event.event_name for row in core.store.read_ledger()] == []


def test_repeated_unknown_references_raise_the_enumeration_signal() -> None:
    core = _core(EnumerationSignal(threshold=2, clock=lambda: 1000))
    with pytest.raises(UnknownReference):
        core.resolve("ref_probe_1", audience="api.github.com", tool="gh", session_id="s1")
    assert core.store.read_ledger() == ()

    with pytest.raises(UnknownReference):
        core.resolve("ref_probe_2", audience="api.github.com", tool="gh", session_id="s1")
    rows = core.store.read_ledger()
    assert len(rows) == 1
    event = rows[0].event
    assert event.event_name == "evasion-detected"
    assert event.severity == "high"
    assert event.reason == "reference-enumeration"
    assert event.session_id == "s1"
    assert event.agent_id == "a1"


def test_probes_outside_the_window_do_not_accumulate() -> None:
    now = {"t": 1000}
    signal = EnumerationSignal(threshold=2, window_seconds=10, clock=lambda: now["t"])
    core = _core(signal)
    with pytest.raises(UnknownReference):
        core.resolve("ref_probe_1", audience="api.github.com", tool="gh", session_id="s1")
    now["t"] = 2000
    with pytest.raises(UnknownReference):
        core.resolve("ref_probe_2", audience="api.github.com", tool="gh", session_id="s1")
    assert core.store.read_ledger() == ()


def test_an_unavailable_store_denies_and_mints_nothing() -> None:
    core = _core()
    core.store.close()
    with pytest.raises(StoreError):
        core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")


def test_a_binding_denial_still_denies_before_any_mint() -> None:
    core = _core()
    with pytest.raises(ResolutionDenied, match="binding-not-allowed"):
        core.resolve("ref_1", audience="other.example", tool="gh", session_id="s1")
    assert core.store.read_ledger() == ()
