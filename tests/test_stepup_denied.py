"""10.1/10.2 — deny, timeout, and a forged approval all mint nothing (SC-34)."""

from __future__ import annotations

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.stepup import (
    AgentPolicyClient,
    PolicyDecision,
    PolicyError,
    StepUpGate,
    StepUpRequest,
)
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

TTL = {"prod": TtlBound(floor=30, ceiling=300)}


def _core(decision: PolicyDecision, *, raise_error: bool = False) -> ResolutionCore:
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
            reference_id="ref_prod",
            backend="keychain",
            path="agentkeys/prod/token",
            class_="prod",
            label="prod token",
        )
    )

    def ask(request: StepUpRequest) -> PolicyDecision:
        if raise_error:
            raise PolicyError("free-text approval is not a decision")
        return decision

    return ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_prod", "api.prod.example", "deploy"),),
        clock=lambda: 1000,
        step_up=StepUpGate(AgentPolicyClient(ask)),
    )


def _resolve(core: ResolutionCore) -> None:
    core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")


def test_a_denied_approval_mints_nothing() -> None:
    core = _core(PolicyDecision(decision="deny", decided_by="agentpolicy", source="human-once"))
    with pytest.raises(ResolutionDenied, match="step-up-denied"):
        _resolve(core)

    names = [row.event.event_name for row in core.store.read_ledger()]
    assert names == ["reference-resolved", "step-up-requested", "step-up-denied"]
    assert core.store.list_live(1000) == ()


def test_a_timeout_is_a_deny() -> None:
    core = _core(PolicyDecision(decision="timeout", decided_by="agentpolicy", source="human-once"))
    with pytest.raises(ResolutionDenied, match="step-up-denied: timeout"):
        _resolve(core)
    assert core.store.list_live(1000) == ()


def test_a_free_text_or_forged_approval_is_refused() -> None:
    core = _core(PolicyDecision(decision="yes", decided_by="agentpolicy", source="human-once"))
    with pytest.raises(ResolutionDenied, match="policy-error"):
        _resolve(core)
    assert core.store.list_live(1000) == ()


def test_the_agent_cannot_approve_itself() -> None:
    core = _core(PolicyDecision(decision="allow", decided_by="a1", source="human-once"))
    with pytest.raises(ResolutionDenied, match="cannot approve"):
        _resolve(core)
    assert core.store.list_live(1000) == ()


def test_a_decision_without_a_source_is_refused() -> None:
    core = _core(PolicyDecision(decision="allow", decided_by="agentpolicy", source=""))
    with pytest.raises(ResolutionDenied, match="authorization.source"):
        _resolve(core)


def test_the_denied_event_is_a_structured_warn() -> None:
    core = _core(PolicyDecision(decision="deny", decided_by="agentpolicy", source="human-once"))
    with pytest.raises(ResolutionDenied):
        _resolve(core)
    denied = next(
        row.event for row in core.store.read_ledger() if row.event.event_name == "step-up-denied"
    )
    assert denied.severity == "warn"
    assert denied.reference_id == "ref_prod"
    assert denied.binding_json is not None


def test_a_local_class_is_not_gated() -> None:
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id="s1",
            agent_id="a1",
            harness="cli",
            started_at=1,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )
    ReferenceRegistry(store).register(
        ReferenceDoc(
            reference_id="ref_dev",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            label="dev token",
        )
    )

    def never_called(request: StepUpRequest) -> PolicyDecision:
        raise AssertionError("dev must not ask for approval")

    core = ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl={"dev": TtlBound(30, 900)},
        bindings=(("ref_dev", "api.dev.example", "gh"),),
        clock=lambda: 1000,
        step_up=StepUpGate(AgentPolicyClient(never_called)),
    )
    core.resolve("ref_dev", audience="api.dev.example", tool="gh", session_id="s1")
    assert [row.event.event_name for row in store.read_ledger()] == [
        "reference-resolved",
        "issuance.created",
    ]
