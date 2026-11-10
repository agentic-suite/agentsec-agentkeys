"""6.5 — time correctness: a clock jump can neither extend nor resurrect a TTL."""

from __future__ import annotations

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore
from agentkeys.time_correctness import ClockSkewError, ExpirySweeper, TimeGuard

TTL = {"dev": TtlBound(floor=30, ceiling=900)}


class Clock:
    def __init__(self, start: int = 1000) -> None:
        self.now = start

    def __call__(self) -> int:
        return self.now


def _guard(clock: Clock, tolerance: int = 0) -> TimeGuard:
    return TimeGuard(clock=clock, skew_tolerance=tolerance)


def test_expiry_uses_absolute_instants() -> None:
    clock = Clock()
    guard = _guard(clock)
    assert guard.deadline(1000, 300) == 1300
    assert guard.is_expired(1300) is False
    clock.now = 1300
    assert guard.is_expired(1300) is True


def test_a_backwards_jump_beyond_tolerance_fails_closed() -> None:
    clock = Clock()
    guard = _guard(clock)
    assert guard.now() == 1000
    clock.now = 900
    with pytest.raises(ClockSkewError):
        guard.now()


def test_a_small_backwards_jump_is_floored_and_cannot_extend_a_ttl() -> None:
    clock = Clock()
    guard = _guard(clock, tolerance=200)
    assert guard.now() == 1000
    clock.now = 900
    # The guard refuses to go backwards: the TTL deadline is unchanged.
    assert guard.now() == 1000
    assert guard.deadline(1000, 300) == 1300
    assert guard.is_expired(1300) is False


def test_a_forwards_jump_expires_but_never_resurrects() -> None:
    clock = Clock()
    guard = _guard(clock)
    assert guard.is_expired(1300) is False
    clock.now = 5000
    assert guard.is_expired(1300) is True


def test_deadline_refuses_a_non_positive_ttl() -> None:
    guard = _guard(Clock())
    with pytest.raises(ValueError):
        guard.deadline(1000, 0)
    with pytest.raises(ValueError):
        guard.deadline(1000, -1)


def _core(store: MemoryStore, clock: Clock) -> ResolutionCore:
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
        clock=clock,
    )


def test_expiry_fires_exactly_once_per_issuance() -> None:
    store = MemoryStore()
    store.open()
    clock = Clock()
    core = _core(store, clock)
    first = core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    clock.now = 4000
    second = core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert first.issuance.issuance_id != second.issuance.issuance_id

    sweeper = ExpirySweeper(store, _guard(clock))
    expired = sweeper.sweep()
    assert {issuance.issuance_id for issuance in expired} == {first.issuance.issuance_id}
    events = [row.event for row in store.read_ledger() if row.event.event_name == "expired"]
    assert len(events) == 1
    assert {event.issuance_id for event in events} == {first.issuance.issuance_id}

    # A second sweep at the same instant finds nothing: expiry fires once, ever.
    assert sweeper.sweep() == ()

    clock.now = 4300
    later = sweeper.sweep()
    assert {issuance.issuance_id for issuance in later} == {second.issuance.issuance_id}
    assert len([row for row in store.read_ledger() if row.event.event_name == "expired"]) == 2
    assert sweeper.sweep() == ()


def test_a_consumed_issuance_is_not_expired() -> None:
    store = MemoryStore()
    store.open()
    clock = Clock()
    core = _core(store, clock)
    resolved = core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert resolved.token is not None
    assert core.use(resolved.issuance.issuance_id, resolved.token, now=1001).status == "consumed"
    clock.now = 4000
    assert ExpirySweeper(store, _guard(clock)).sweep() == ()
