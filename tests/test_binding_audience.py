"""4.5 - audience/replay enforcement: SC-08-SC-11 + SC-42 all fail closed and are logged."""

from __future__ import annotations

import pytest

from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import (
    AudienceMismatch,
    InjectionDenied,
    InjectionRequest,
    WideningRefused,
)
from agentkeys.egress.enforce import Decision, RejectionLog, check_injection
from agentkeys.egress.env import EnvInjector

EXPECTED = "api.github.com"


def _resolved(
    audience: str = EXPECTED, tool: str = "gh", token: str | None = "tok"
) -> ResolvedIssuance:
    doc = IssuanceDoc(
        issuance_id="iss_1",
        reference_id="ref_1",
        session_id="s1",
        agent_id="a1",
        binding=Binding(audience=audience, tool=tool),
        class_="dev",
        ttl=300,
        issued_at=1000,
        expires_at=1300,
    )
    return ResolvedIssuance(issuance=doc, token=token)


def test_a_matching_request_is_allowed() -> None:
    decision = check_injection(
        _resolved(), InjectionRequest(audience=EXPECTED, tool="gh"), EXPECTED
    )
    assert decision == Decision(allowed=True)


@pytest.mark.parametrize(
    ("asked", "injector_audience", "reason"),
    [
        (InjectionRequest(audience="replay.example", tool="gh"), EXPECTED, "audience-mismatch"),
        (InjectionRequest(audience=EXPECTED, tool="other"), EXPECTED, "widening-refused"),
        (InjectionRequest(audience=EXPECTED, tool="gh"), "replay.example", "audience-mismatch"),
    ],
)
def test_replays_and_widening_are_denied(
    asked: InjectionRequest, injector_audience: str, reason: str
) -> None:
    decision = check_injection(_resolved(), asked, injector_audience)
    assert decision.allowed is False and decision.reason == reason


def test_the_injector_itself_refuses_a_cross_audience_replay() -> None:
    with pytest.raises(AudienceMismatch):
        EnvInjector(EXPECTED).apply(
            _resolved(audience="other.example"),
            request=InjectionRequest(audience="other.example", tool="gh"),
            now=1001,
        )


def test_a_cross_tool_replay_is_a_widening_refusal() -> None:
    with pytest.raises(WideningRefused):
        EnvInjector(EXPECTED).apply(
            _resolved(), request=InjectionRequest(audience=EXPECTED, tool="git"), now=1001
        )


def test_a_stale_issuance_cannot_be_replayed() -> None:
    with pytest.raises(InjectionDenied, match="expired"):
        EnvInjector(EXPECTED).apply(
            _resolved(), request=InjectionRequest(audience=EXPECTED, tool="gh"), now=9999
        )


def test_every_refusal_is_logged_as_exchange_rejected() -> None:
    log = RejectionLog()
    event = log.record(
        issuance_id="iss_1", reason="audience-mismatch", audience=EXPECTED, tool="gh"
    )
    assert event.event_name == "exchange-rejected"
    assert log.events() == (event,)


def test_a_denial_object_can_be_logged_directly() -> None:
    log = RejectionLog()
    denial = InjectionDenied("token-unavailable")
    log.record_denial(denial, issuance_id="iss_1")
    assert log.events()[0].reason == "token-unavailable"
