"""2.4/2.5 - resolution: idempotent per (reference, binding) window, single-use consume."""

from __future__ import annotations

import hashlib
from typing import cast

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.issuance import IssuanceDoc
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.core.resolution import (
    ResolutionCore,
    ResolutionDenied,
    ResolvedIssuance,
    UseResult,
)
from agentkeys.store.contract import LedgerEvent, Session
from agentkeys.store.memory import MemoryStore

TTL = {"dev": TtlBound(floor=30, ceiling=900)}
BINDINGS = (("ref_1", "api.github.com", "gh"),)


class Clock:
    def __init__(self, start: int = 1000) -> None:
        self.now = start

    def __call__(self) -> int:
        return self.now


def _revoked_event() -> LedgerEvent:
    return LedgerEvent(
        event_id="rev1",
        event_version="1.0",
        event_name="revoked",
        occurred_at=1500,
        monotonic_ms=1,
        session_id="s1",
        agent_id="a1",
        reference_id=None,
        issuance_id=None,
        binding_json=None,
        ttl_seconds=None,
        principal="op",
        reason="operator",
        severity="high",
    )


@pytest.fixture
def core() -> ResolutionCore:
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
    registry = ReferenceRegistry(store)
    registry.register(
        ReferenceDoc(
            reference_id="ref_1",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            label="dev token",
        )
    )
    return ResolutionCore(store, registry, ttl=TTL, bindings=BINDINGS, clock=Clock())


def _resolve(core: ResolutionCore) -> ResolvedIssuance:
    return core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")


def test_resolve_mints_a_bound_single_use_issuance(core: ResolutionCore) -> None:
    resolved = _resolve(core)
    assert isinstance(resolved.issuance, IssuanceDoc)
    assert resolved.issuance.issued_at == 1000
    assert resolved.issuance.ttl == 300
    assert resolved.issuance.binding_key() == ("api.github.com", "gh", "s1")
    assert resolved.token is not None
    assert len(resolved.token) == 32
    stored = core.store.get_issuance(resolved.issuance.issuance_id)
    assert stored is not None
    assert stored.secret_hash == hashlib.sha256(resolved.token.encode()).hexdigest()


def test_a_retry_in_the_window_returns_the_same_issuance_and_token(core: ResolutionCore) -> None:
    first = _resolve(core)
    second = _resolve(core)
    assert first.issuance == second.issuance
    assert first.token == second.token
    created = [r for r in core.store.read_ledger() if r.event.event_name == "issuance.created"]
    assert len(created) == 1


def test_a_new_window_mints_a_new_issuance(core: ResolutionCore) -> None:
    first = _resolve(core)
    cast(Clock, core.clock).now = 2000
    second = _resolve(core)
    assert second.issuance.issuance_id != first.issuance.issuance_id


def test_the_token_is_transient_across_processes(core: ResolutionCore) -> None:
    first = _resolve(core)
    fresh = ResolutionCore(core.store, core.registry, ttl=TTL, bindings=BINDINGS, clock=core.clock)
    retried = fresh.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert retried.issuance == first.issuance
    assert retried.token is None


def test_an_unknown_reference_is_denied(core: ResolutionCore) -> None:
    with pytest.raises(UnknownReference, match="unknown reference_id"):
        core.resolve("ref_nope", audience="api.github.com", tool="gh", session_id="s1")


def test_a_binding_outside_the_allowlist_is_denied(core: ResolutionCore) -> None:
    with pytest.raises(ResolutionDenied, match="binding-not-allowed"):
        core.resolve("ref_1", audience="other.example", tool="gh", session_id="s1")


def test_a_revoked_session_is_denied(core: ResolutionCore) -> None:
    core.store.cas_revoke(
        scope="session",
        target_id="s1",
        requested_by="op",
        requested_at=1500,
        reason="operator",
        event=_revoked_event(),
    )
    with pytest.raises(ResolutionDenied, match="session-revoked"):
        _resolve(core)


def test_an_unknown_session_is_denied(core: ResolutionCore) -> None:
    with pytest.raises(ResolutionDenied, match="unknown-session"):
        core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="ghost")


def test_use_consumes_once_and_replays_are_rejected(core: ResolutionCore) -> None:
    resolved = _resolve(core)
    assert resolved.token is not None
    assert core.use(resolved.issuance.issuance_id, resolved.token, now=1001).status == "consumed"
    assert core.use(resolved.issuance.issuance_id, resolved.token, now=1002) == UseResult(
        status="already_consumed"
    )
    stored = core.store.get_issuance(resolved.issuance.issuance_id)
    assert stored is not None and stored.consumed_at == 1001


def test_a_wrong_token_is_rejected_not_silently_passed(core: ResolutionCore) -> None:
    resolved = _resolve(core)
    assert core.use(resolved.issuance.issuance_id, "0" * 32, now=1001) == UseResult(
        status="rejected"
    )


def test_an_expired_token_is_expired(core: ResolutionCore) -> None:
    resolved = _resolve(core)
    assert resolved.token is not None
    assert core.use(resolved.issuance.issuance_id, resolved.token, now=5000).status == "expired"


def test_use_of_an_unknown_issuance_is_typed(core: ResolutionCore) -> None:
    assert core.use("iss_missing", "x" * 32, now=1001) == UseResult(status="unknown")


def test_the_core_never_exposes_a_stored_secret(core: ResolutionCore) -> None:
    assert not hasattr(core, "get_secret")
    assert not hasattr(core, "resolve_value")
    assert all(isinstance(doc, ReferenceDoc) for doc in core.list_references())
