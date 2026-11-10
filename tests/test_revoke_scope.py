"""6.1/6.4/6.6 — revoke scopes, replay refusal, and the attributed `revoked` event."""

from __future__ import annotations

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.revoke import Revoker, UnknownTarget
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

TTL = {"dev": TtlBound(floor=30, ceiling=900)}


class Clock:
    def __init__(self, start: int = 1000) -> None:
        self.now = start

    def __call__(self) -> int:
        return self.now


def _seed() -> MemoryStore:
    store = MemoryStore()
    store.open()
    for session_id, agent_id in (("s1", "a1"), ("s2", "a2"), ("s3", "a1")):
        store.create_session(
            Session(
                session_id=session_id,
                agent_id=agent_id,
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
    return store


def _core(store: MemoryStore, clock: Clock) -> ResolutionCore:
    return ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_1", "api.github.com", "gh"),),
        clock=clock,
    )


def _resolve(core: ResolutionCore, session_id: str) -> None:
    core.resolve("ref_1", audience="api.github.com", tool="gh", session_id=session_id)


def _revoked_names(store: MemoryStore) -> list[str]:
    return [row.event.session_id or "" for row in store.read_ledger()]


def test_session_revoke_kills_exactly_one_session() -> None:
    store = _seed()
    core = _core(store, Clock())
    outcome = Revoker(store, clock=Clock()).revoke(
        "session", "s1", reason="operator", requested_by="alice"
    )

    assert len(outcome.revocations) == 1
    assert outcome.revocations[0].winner is True
    with pytest.raises(ResolutionDenied, match="session-revoked"):
        _resolve(core, "s1")
    _resolve(core, "s2")
    _resolve(core, "s3")


def test_a_token_minted_before_revoke_stops_authenticating() -> None:
    store = _seed()
    clock = Clock()
    core = _core(store, clock)
    resolved = core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert resolved.token is not None

    Revoker(store, clock=clock).revoke("session", "s1", reason="kill", requested_by="alice")

    assert core.use(resolved.issuance.issuance_id, resolved.token, now=1001).status == "rejected"


def test_agent_revoke_kills_only_that_agents_sessions() -> None:
    store = _seed()
    core = _core(store, Clock())
    outcome = Revoker(store, clock=Clock()).revoke(
        "agent", "a1", reason="operator", requested_by="alice"
    )

    assert len(outcome.revocations) == 2
    for session_id in ("s1", "s3"):
        with pytest.raises(ResolutionDenied):
            _resolve(core, session_id)
    _resolve(core, "s2")


def test_all_is_explicit_and_kills_every_session() -> None:
    store = _seed()
    core = _core(store, Clock())
    outcome = Revoker(store, clock=Clock()).revoke(
        "all", None, reason="incident", requested_by="alice"
    )

    assert len(outcome.revocations) == 3
    for session_id in ("s1", "s2", "s3"):
        with pytest.raises(ResolutionDenied):
            _resolve(core, session_id)


def test_unknown_target_is_a_loud_error() -> None:
    store = _seed()
    with pytest.raises(UnknownTarget, match="ghost"):
        Revoker(store, clock=Clock()).revoke(
            "session", "ghost", reason="operator", requested_by="alice"
        )
    with pytest.raises(UnknownTarget, match="ghost-agent"):
        Revoker(store, clock=Clock()).revoke(
            "agent", "ghost-agent", reason="operator", requested_by="alice"
        )


def test_all_with_no_sessions_is_a_loud_error() -> None:
    store = MemoryStore()
    store.open()
    with pytest.raises(UnknownTarget):
        Revoker(store, clock=Clock()).revoke("all", None, reason="operator", requested_by="alice")


def test_unknown_scope_is_refused() -> None:
    store = _seed()
    with pytest.raises(ValueError, match="scope"):
        Revoker(store, clock=Clock()).revoke(
            "galaxy", "s1", reason="operator", requested_by="alice"
        )


def test_revoked_event_carries_scope_target_operator_and_time() -> None:
    store = _seed()
    outcome = Revoker(store, clock=Clock(start=1234)).revoke(
        "session", "s1", reason="operator", requested_by="alice"
    )

    event = outcome.events[0]
    assert event.event_name == "revoked"
    assert event.severity == "high"
    assert event.session_id == "s1"
    assert event.agent_id == "a1"
    assert event.principal == "alice"
    assert event.reason == "operator"
    assert event.occurred_at == 1234
    assert event.monotonic_ms >= 0

    rows = [row for row in store.read_ledger() if row.event.event_name == "revoked"]
    assert len(rows) == 1
    revocation = store.get_revocation(outcome.revocations[0].revocation.revocation_id)
    assert revocation is not None
    assert revocation.requested_by == "alice"
    assert revocation.effective_at == 1234


def test_a_second_revoke_of_the_same_target_is_idempotent() -> None:
    store = _seed()
    revoker = Revoker(store, clock=Clock())
    first = revoker.revoke("session", "s1", reason="operator", requested_by="alice")
    second = revoker.revoke("session", "s1", reason="operator", requested_by="alice")

    assert first.revocations[0].winner is True
    assert second.revocations[0].winner is False
    assert second.revocations[0].epoch_after == 1
