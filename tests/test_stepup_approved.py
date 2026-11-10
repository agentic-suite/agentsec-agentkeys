"""10.1/10.2 — an approved prod mint is recorded, bounded, and never asked twice in a window."""

from __future__ import annotations

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.stepup import AgentPolicyClient, PolicyDecision, StepUpGate, StepUpRequest
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

TTL = {"prod": TtlBound(floor=30, ceiling=300)}


def _core(decision: PolicyDecision | None = None) -> tuple[ResolutionCore, list[StepUpRequest]]:
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
    calls: list[StepUpRequest] = []
    answer = decision or PolicyDecision(
        decision="allow", decided_by="agentpolicy", source="human-once"
    )

    def ask(request: StepUpRequest) -> PolicyDecision:
        calls.append(request)
        return answer

    core = ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_prod", "api.prod.example", "deploy"),),
        clock=lambda: 1000,
        ttl_seconds=120,
        step_up=StepUpGate(AgentPolicyClient(ask)),
    )
    return core, calls


def test_a_prod_mint_requires_and_records_an_approval() -> None:
    core, calls = _core()
    resolved = core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")

    assert len(calls) == 1
    request = calls[0]
    assert request.class_ == "prod"
    assert request.agent_id == "a1"
    assert request.session_id == "s1"
    assert request.audience == "api.prod.example"
    assert request.tool == "deploy"

    issuance = core.get_issuance(resolved.issuance.issuance_id)
    assert issuance is not None
    assert issuance.provenance == {
        "decided_by": "agentpolicy",
        "decision": "allow",
        "source": "human-once",
    }
    assert issuance.ttl == 120


def test_the_upgrade_is_in_the_ledger() -> None:
    core, _calls = _core()
    resolved = core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")
    names = [row.event.event_name for row in core.store.read_ledger()]
    assert names == [
        "reference-resolved",
        "step-up-requested",
        "issuance.created",
        "step-up-granted",
    ]
    granted = next(
        row.event for row in core.store.read_ledger() if row.event.event_name == "step-up-granted"
    )
    assert granted.issuance_id == resolved.issuance.issuance_id
    assert granted.reason == "agentpolicy"
    assert granted.principal == "op"
    stored = core.store.get_issuance(resolved.issuance.issuance_id)
    assert stored is not None
    assert "agentpolicy" in stored.provenance_json


def test_a_retry_in_the_window_does_not_ask_again() -> None:
    core, calls = _core()
    first = core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")
    second = core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")
    assert first.issuance == second.issuance
    assert len(calls) == 1


def test_a_new_window_asks_again() -> None:
    core, calls = _core()
    core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")
    core.clock = lambda: 2000
    core.resolve("ref_prod", audience="api.prod.example", tool="deploy", session_id="s1")
    assert len(calls) == 2
