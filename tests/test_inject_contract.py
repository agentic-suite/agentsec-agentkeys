"""4.1 - the injection contract: binding is the ceiling, denials are typed, drivers forget."""

from __future__ import annotations

import pytest

from agentkeys.backends.contract import SecretValue
from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import (
    AudienceMismatch,
    BaseInjector,
    Injection,
    InjectionDenied,
    InjectionRequest,
    WideningRefused,
    rejection_event,
)


def _resolved(
    audience: str = "api.github.com",
    tool: str = "gh",
    expires_at: int = 1300,
    token: str | None = "tok",
) -> ResolvedIssuance:
    doc = IssuanceDoc(
        issuance_id="iss_1",
        reference_id="ref_1",
        session_id="s1",
        agent_id="a1",
        binding=Binding(audience=audience, tool=tool),
        class_="dev",
        ttl=expires_at - 900,
        issued_at=900,
        expires_at=expires_at,
    )
    return ResolvedIssuance(issuance=doc, token=token)


class DummyInjector(BaseInjector):
    kind = "env"

    def _deliver(self, resolved: ResolvedIssuance, request: InjectionRequest) -> Injection:
        value = resolved.token or ""
        return Injection(
            kind=self.kind,
            audience=self.target_audience(),
            secret=SecretValue(value),
            env={"TOKEN": value},
        )


def _request(
    audience: str = "api.github.com", tool: str = "gh", client: str | None = None
) -> InjectionRequest:
    return InjectionRequest(audience=audience, tool=tool, client_token=client)


def test_a_request_within_the_binding_is_injected() -> None:
    injection = DummyInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    assert isinstance(injection, Injection)
    assert injection.audience == "api.github.com"
    assert injection.secret.reveal() == "tok"
    assert injection.env == {"TOKEN": "tok"}


@pytest.mark.parametrize(
    ("asked", "error"),
    [
        (_request(audience="other.example"), AudienceMismatch),
        (_request(tool="other-tool"), WideningRefused),
    ],
)
def test_widening_the_binding_is_refused(asked: InjectionRequest, error: type) -> None:
    with pytest.raises(error):
        DummyInjector("api.github.com").apply(_resolved(), request=asked, now=1001)


def test_an_injector_for_another_audience_refuses_everything() -> None:
    with pytest.raises(AudienceMismatch):
        DummyInjector("elsewhere.example").apply(_resolved(), request=_request(), now=1001)


def test_an_expired_issuance_cannot_be_injected() -> None:
    with pytest.raises(InjectionDenied, match="expired"):
        DummyInjector("api.github.com").apply(
            _resolved(expires_at=1000), request=_request(), now=1001
        )


def test_a_token_unavailable_in_this_process_is_denied() -> None:
    with pytest.raises(InjectionDenied, match="token-unavailable"):
        DummyInjector("api.github.com").apply(_resolved(token=None), request=_request(), now=1001)


def test_forget_clears_what_the_driver_held() -> None:
    injector = DummyInjector("api.github.com")
    injector.apply(_resolved(), request=_request(), now=1001)
    assert injector.retained() == 1
    injector.forget()
    assert injector.retained() == 0


def test_a_denial_becomes_an_exchange_rejected_event() -> None:
    event = rejection_event(
        issuance_id="iss_1",
        reason="audience-mismatch",
        audience="api.github.com",
        occurred_at=1002,
    )
    assert event.event_name == "exchange-rejected"
    assert event.severity == "warn"
    assert event.issuance_id == "iss_1"
    assert event.reason == "audience-mismatch"


def test_the_client_token_is_stripped_and_never_injected() -> None:
    injection = DummyInjector("api.github.com").apply(
        _resolved(), request=_request(client="client-supplied-token"), now=1001
    )
    assert injection.overwrote_client_credential is True
    assert "client-supplied-token" not in str(injection.env)


def test_denial_reasons_are_the_documented_set() -> None:
    assert set(InjectionDenied.REASONS) == {
        "widening-refused",
        "audience-mismatch",
        "expired",
        "token-unavailable",
        "passthrough-stripped",
        "injector-unavailable",
    }
