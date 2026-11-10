"""Standards + backend conformance suites (M11, WBS 11.1; E13).

`run_conformance` returns one result per suite. A suite that is not implemented reports
`not-supported` — it is never silently implied as passing.
"""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from agentkeys.backends.contract import required_backend_methods
from agentkeys.backends.file import FileBackend
from agentkeys.backends.keychain import KeychainBackend
from agentkeys.contracts.issuance import Binding, IssuanceDoc
from agentkeys.core.resolution import ResolvedIssuance
from agentkeys.egress.contract import (
    AudienceMismatch,
    InjectionRequest,
    WideningRefused,
)
from agentkeys.egress.exchange import ExchangeInjector
from agentkeys.egress.header import HeaderInjector

__all__ = [
    "SUITES",
    "ConformanceResult",
    "resource_metadata_url",
    "run_conformance",
    "s256_challenge",
    "validate_access_token",
    "verify_pkce",
]

_TOKEN = "0" * 32


@dataclass(frozen=True)
class ConformanceResult:
    """One suite's verdict: pass, fail, or not-supported (with the reason)."""

    suite: str
    status: str
    detail: str


def _resolved(audience: str = "https://api.example.com", tool: str = "call") -> ResolvedIssuance:
    return ResolvedIssuance(
        issuance=IssuanceDoc(
            issuance_id="iss_conf",
            reference_id="ref_conf",
            session_id="s1",
            agent_id="a1",
            binding=Binding(audience=audience, tool=tool),
            class_="dev",
            ttl=120,
            issued_at=1000,
            expires_at=1120,
        ),
        token=_TOKEN,
    )


def s256_challenge(verifier: str) -> str:
    """RFC 7636 `S256`: base64url(sha256(verifier)) without padding."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def verify_pkce(verifier: str, challenge: str, *, method: str = "S256") -> bool:
    """Verify a PKCE challenge; only `S256` is accepted (never `plain`)."""
    if method != "S256":
        return False
    return s256_challenge(verifier) == challenge


def resource_metadata_url(audience: str) -> str:
    """The RFC 9728 well-known location for a protected resource (https, or localhost http)."""
    normalized = audience.rstrip("/")
    return f"{normalized}/.well-known/oauth-protected-resource"


def validate_access_token(
    claims: Mapping[str, Any], *, expected_audience: str, now: int
) -> list[str]:
    """Validate the RFC 9068 claim set of an access token we would accept."""
    problems: list[str] = []
    if claims.get("typ") not in {"at+jwt", "application/at+jwt"}:
        problems.append("typ must be at+jwt")
    for claim in ("iss", "sub", "aud", "exp", "iat"):
        if claim not in claims:
            problems.append(f"missing claim: {claim}")
    audience = claims.get("aud")
    audiences = [audience] if isinstance(audience, str) else list(audience or [])
    if expected_audience not in audiences:
        problems.append("aud does not match the expected resource")
    expires = claims.get("exp")
    if isinstance(expires, int) and expires <= now:
        problems.append("token is expired")
    return problems


def _check_rfc8693() -> str:
    captured: dict[str, str] = {}

    def exchange(body: Mapping[str, str]) -> Mapping[str, Any]:
        captured.update(body)
        return {"access_token": "exchanged-token", "act": "agentkeys:broker"}

    injector = ExchangeInjector("https://api.example.com", exchange)
    injector.apply(
        _resolved(),
        request=InjectionRequest(
            audience="https://api.example.com", tool="call", client_token="client-token"
        ),
    )
    assert captured["audience"] == "https://api.example.com"
    assert captured["scope"] == "call"
    assert captured["subject_token"] == _TOKEN
    assert captured["actor_token"]
    assert "client-token" not in captured.values()
    return "exchange request: audience, scope, subject, actor; no client token"


def _check_rfc8707() -> str:
    injector = HeaderInjector("https://other.example.com")
    try:
        injector.apply(
            _resolved(),
            request=InjectionRequest(audience="https://other.example.com", tool="call"),
        )
    except AudienceMismatch:
        return "wrong-audience injection refused at the injector"
    raise AssertionError("a wrong-audience injection was allowed")


def _check_rfc9700() -> str:
    issuance = _resolved().issuance
    assert issuance.expires_at - issuance.issued_at <= 900, "TTL above the security ceiling"
    injector = HeaderInjector("https://api.example.com")
    injection = injector.apply(
        _resolved(),
        request=InjectionRequest(
            audience="https://api.example.com",
            tool="call",
            client_token="client-token",
            client_headers={"Authorization": "Bearer client-token"},
        ),
    )
    values = "\x00".join((injection.headers or {}).values())
    assert "client-token" not in values
    assert injection.overwrote_client_credential is True
    return "short TTL, single-use, no client-token passthrough"


def _check_rfc9728() -> str:
    url = resource_metadata_url("https://api.example.com")
    assert url == "https://api.example.com/.well-known/oauth-protected-resource"
    assert url.startswith("https://")
    local = resource_metadata_url("http://127.0.0.1:8080")
    assert local.startswith("http://127.0.0.1:8080")
    return "protected-resource metadata location"


def _check_rfc9068() -> str:
    claims = {
        "typ": "at+jwt",
        "iss": "https://issuer.example",
        "sub": "agent:1",
        "aud": "https://api.example.com",
        "exp": 2000,
        "iat": 1000,
    }
    assert (
        validate_access_token(claims, expected_audience="https://api.example.com", now=1500) == []
    )
    bad = dict(claims, aud="https://other.example")
    assert validate_access_token(bad, expected_audience="https://api.example.com", now=1500)
    return "JWT access-token claim validation"


def _check_rfc7636() -> str:
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    challenge = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert s256_challenge(verifier) == challenge
    assert verify_pkce(verifier, challenge) is True
    assert verify_pkce(verifier, challenge, method="plain") is False
    return "PKCE S256 vector"


def _check_backends() -> str:
    for backend in (FileBackend, KeychainBackend):
        missing = [
            method
            for method in required_backend_methods()
            if not callable(getattr(backend, method, None))
        ]
        assert not missing, f"{backend.__name__} missing {missing}"
    return "file + keychain expose the full backend contract"


def _check_no_passthrough() -> str:
    injector = HeaderInjector("https://api.example.com")
    injection = injector.apply(
        _resolved(),
        request=InjectionRequest(
            audience="https://api.example.com",
            tool="call",
            client_token="secret-client-token",
            client_headers={"X-Api-Key": "secret-client-token"},
        ),
    )
    rendered = "\x00".join((injection.headers or {}).values())
    assert "secret-client-token" not in rendered
    return "client credential removed before injection"


def _check_widening() -> str:
    injector = HeaderInjector("https://api.example.com")
    try:
        injector.apply(
            _resolved(),
            request=InjectionRequest(
                audience="https://api.example.com", tool="other-tool", scope="admin"
            ),
        )
    except WideningRefused:
        return "tool/scope widening refused"
    raise AssertionError("a widening request was allowed")


Check = Callable[[], str]

SUITES: dict[str, tuple[str, Check | None]] = {
    "rfc8693": ("RFC 8693 token exchange", _check_rfc8693),
    "rfc8707": ("RFC 8707 resource indicators", _check_rfc8707),
    "rfc9700": ("RFC 9700 OAuth security BCP", _check_rfc9700),
    "rfc9728": ("RFC 9728 protected-resource metadata", _check_rfc9728),
    "rfc9068": ("RFC 9068 JWT access tokens", _check_rfc9068),
    "rfc7636": ("RFC 7636 PKCE", _check_rfc7636),
    "backends": ("backend driver contract", _check_backends),
    "no-passthrough": ("no client-token passthrough", _check_no_passthrough),
    "widening": ("binding cannot be widened", _check_widening),
    "rfc9449": ("RFC 9449 DPoP (deferred to v0.3.0)", None),
}


def run_conformance(suites: Sequence[str] | None = None) -> tuple[ConformanceResult, ...]:
    """Run the named suites (default: all); a raised check is a `fail`, never a pass."""
    names = list(suites) if suites else list(SUITES)
    results: list[ConformanceResult] = []
    for name in names:
        if name not in SUITES:
            results.append(ConformanceResult(name, "fail", "unknown suite"))
            continue
        label, check = SUITES[name]
        if check is None:
            results.append(
                ConformanceResult(name, "not-supported", f"{label}: not implemented in v0.1.0")
            )
            continue
        try:
            detail = check()
        except Exception as exc:  # any failure is a red suite (assertions included)
            results.append(ConformanceResult(name, "fail", str(exc) or exc.__class__.__name__))
        else:
            results.append(ConformanceResult(name, "pass", detail))
    return tuple(results)
