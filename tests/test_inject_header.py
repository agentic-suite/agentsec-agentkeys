"""4.3 - HTTP header driver: bound token attached, client credential overwritten."""

from __future__ import annotations

from types import MappingProxyType

from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import InjectionRequest
from agentkeys.egress.header import HeaderInjector


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
    return ResolvedIssuance(issuance=doc, token="scoped-token")


def _request(headers: dict[str, str] | None = None) -> InjectionRequest:
    return InjectionRequest(
        audience="api.github.com",
        tool="gh",
        client_headers=MappingProxyType(headers or {}),
    )


def test_the_bound_token_is_attached_as_a_bearer_header() -> None:
    injection = HeaderInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    assert injection.headers == {"Authorization": "Bearer scoped-token"}


def test_a_client_supplied_credential_is_overwritten() -> None:
    injection = HeaderInjector("api.github.com").apply(
        _resolved(),
        request=_request({"Authorization": "Bearer client-token", "Accept": "application/json"}),
        now=1001,
    )
    assert injection.headers is not None
    assert injection.headers["Authorization"] == "Bearer scoped-token"
    assert injection.headers["Accept"] == "application/json"
    assert injection.overwrote_client_credential is True


def test_other_credential_headers_are_removed_too() -> None:
    injection = HeaderInjector("api.github.com").apply(
        _resolved(),
        request=_request({"X-Api-Key": "client-key", "api-key": "client-key-2"}),
        now=1001,
    )
    assert injection.headers is not None
    assert "X-Api-Key" not in injection.headers and "api-key" not in injection.headers


def test_the_scheme_and_header_are_configurable() -> None:
    injector = HeaderInjector("api.github.com", header="X-Agent-Key", scheme="")
    injection = injector.apply(_resolved(), request=_request(), now=1001)
    assert injection.headers == {"X-Agent-Key": "scoped-token"}


def test_the_agent_never_sees_the_header_in_a_response_object() -> None:
    injection = HeaderInjector("api.github.com").apply(_resolved(), request=_request(), now=1001)
    assert "scoped-token" not in repr(injection.secret)
    assert "scoped-token" not in str(injection.secret)
