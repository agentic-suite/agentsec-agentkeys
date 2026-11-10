"""4.2 - env-virtualization: the child gets the scoped value, the parent and transcript do not."""

from __future__ import annotations

import os

import pytest

from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import InjectionDenied, InjectionRequest
from agentkeys.egress.env import EnvInjector


def _resolved(token: str | None = "scoped-token") -> ResolvedIssuance:
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
    return ResolvedIssuance(issuance=doc, token=token)


def _request(client: str | None = None) -> InjectionRequest:
    return InjectionRequest(audience="api.github.com", tool="gh", client_token=client)


def test_the_child_environment_carries_only_the_scoped_value() -> None:
    injection = EnvInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    assert injection.env == {"AGENTKEYS_SCOPED_TOKEN": "scoped-token"}
    assert injection.kind == "env"


def test_the_variable_name_is_configurable() -> None:
    injector = EnvInjector("api.github.com", variable="GITHUB_TOKEN")
    injection = injector.apply(_resolved(), request=_request(), now=1001)
    assert injection.env == {"GITHUB_TOKEN": "scoped-token"}


def test_an_invalid_variable_name_is_refused() -> None:
    with pytest.raises(ValueError, match="variable"):
        EnvInjector("api.github.com", variable="not a name")


def test_the_reference_is_never_in_the_child_environment() -> None:
    injection = EnvInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    rendered = "\x00".join((injection.env or {}).values())
    assert "akref" not in rendered and "ref_1" not in rendered


def test_the_parent_environment_is_not_touched() -> None:
    before = dict(os.environ)
    EnvInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    assert dict(os.environ) == before


def test_a_client_token_is_not_forwarded_into_the_child_environment() -> None:
    injection = EnvInjector("api.github.com").apply(
        _resolved(), request=_request(client="client-token"), now=1001
    )
    assert "client-token" not in "\x00".join((injection.env or {}).values())
    assert injection.overwrote_client_credential is True


def test_forget_clears_the_delivered_value() -> None:
    injector = EnvInjector("api.github.com")
    injector.apply(_resolved(), request=_request(), now=1001)
    injector.forget()
    assert injector.retained() == 0


def test_the_driver_refuses_an_issuance_without_a_transient_token() -> None:
    with pytest.raises(InjectionDenied, match="token-unavailable"):
        EnvInjector("api.github.com").apply(_resolved(token=None), request=_request(), now=1001)
