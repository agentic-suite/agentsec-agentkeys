"""4.4 - RFC 8693 exchange: narrow token, actor semantics, no passthrough."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import InjectionDenied, InjectionRequest
from agentkeys.egress.exchange import ExchangeInjector


class Recorder:
    def __init__(self, response: Mapping[str, Any] | None = None) -> None:
        self.bodies: list[Mapping[str, str]] = []
        default = {"access_token": "narrow-token", "act": "agentkeys:broker"}
        self.response = default if response is None else dict(response)

    def __call__(self, body: Mapping[str, str]) -> Mapping[str, Any]:
        self.bodies.append(body)
        return self.response


def _resolved() -> ResolvedIssuance:
    doc = IssuanceDoc(
        issuance_id="iss_1",
        reference_id="ref_1",
        session_id="s1",
        agent_id="a1",
        binding=Binding(audience="api.github.com", tool="gh"),
        class_="dev",
        ttl=300,
        issued_at=1000,
        expires_at=1300,
    )
    return ResolvedIssuance(issuance=doc, token="broker-subject-token")


def _request(client: str | None = None) -> InjectionRequest:
    return InjectionRequest(audience="api.github.com", tool="gh", client_token=client)


def test_the_exchange_requests_one_audience_and_one_scope() -> None:
    recorder = Recorder()
    injection = ExchangeInjector("api.github.com", recorder).apply(
        _resolved(), request=_request(), now=1001
    )
    body = recorder.bodies[0]
    assert body["audience"] == "api.github.com"
    assert body["scope"] == "gh"
    assert body["grant_type"] == "urn:ietf:params:oauth:grant-type:token-exchange"
    assert body["subject_token"] == "broker-subject-token"
    assert body["subject_token_type"] == "urn:ietf:params:oauth:token-type:access_token"
    assert body["actor_token"]
    assert injection.token is not None and injection.token.reveal() == "narrow-token"
    assert injection.actor == "agentkeys:broker"


def test_the_broker_token_is_the_subject_not_the_client_token() -> None:
    recorder = Recorder()
    ExchangeInjector("api.github.com", recorder).apply(
        _resolved(), request=_request(client="client-token"), now=1001
    )
    body = recorder.bodies[0]
    assert "client-token" not in body.values()
    assert body["subject_token"] == "broker-subject-token"


def test_an_exchange_without_a_token_is_a_denial() -> None:
    recorder = Recorder(response={})
    with pytest.raises(InjectionDenied, match="injector-unavailable"):
        ExchangeInjector("api.github.com", recorder).apply(
            _resolved(), request=_request(), now=1001
        )


def test_the_requested_audience_is_the_binding_audience() -> None:
    recorder = Recorder()
    injector = ExchangeInjector("api.github.com", recorder)
    body = injector.request_body(_resolved(), _request())
    assert body["audience"] == injector.target_audience()


def test_forget_clears_the_exchanged_token() -> None:
    recorder = Recorder()
    injector = ExchangeInjector("api.github.com", recorder)
    injector.apply(_resolved(), request=_request(), now=1001)
    injector.forget()
    assert injector.retained() == 0
