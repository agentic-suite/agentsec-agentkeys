"""11.1 — the conformance kit: every aligned suite passes; unsupported is explicit (E13)."""

from __future__ import annotations

import json

import pytest

import agentkeys.conformance as conformance
from agentkeys.cli import main
from agentkeys.conformance import (
    SUITES,
    resource_metadata_url,
    run_conformance,
    s256_challenge,
    validate_access_token,
    verify_pkce,
)


def test_every_aligned_suite_passes() -> None:
    results = run_conformance()
    failed = [result for result in results if result.status == "fail"]
    assert failed == []
    aligned = [result for result in results if result.suite != "rfc9449"]
    assert aligned and all(result.status == "pass" for result in aligned)


def test_an_unsupported_standard_is_never_implied() -> None:
    results = run_conformance(["rfc9449"])
    assert results[0].status == "not-supported"
    assert "not implemented" in results[0].detail


def test_a_broken_check_turns_the_suite_red(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken() -> str:
        raise AssertionError("planted conformance failure")

    monkeypatch.setitem(conformance.SUITES, "rfc7636", ("broken", broken))
    result = run_conformance(["rfc7636"])[0]
    assert result.status == "fail"
    assert "planted" in result.detail


def test_an_unknown_suite_is_a_failure() -> None:
    result = run_conformance(["not-a-suite"])[0]
    assert result.status == "fail"
    assert "unknown suite" in result.detail


def test_rfc9728_metadata_location_and_pkce_vector() -> None:
    assert (
        resource_metadata_url("https://api.example.com")
        == "https://api.example.com/.well-known/oauth-protected-resource"
    )
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    assert s256_challenge(verifier) == "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"
    assert verify_pkce(verifier, s256_challenge(verifier))
    assert not verify_pkce(verifier, s256_challenge(verifier), method="plain")


def test_rfc9068_claim_validation_reports_problems() -> None:
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
    assert validate_access_token(
        dict(claims, aud="https://other.example"),
        expected_audience="https://api.example.com",
        now=1500,
    )
    assert "expired" in " ".join(
        validate_access_token(claims, expected_audience="https://api.example.com", now=3000)
    )


def test_the_conformance_cli_runs_every_suite(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["conformance", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["passed"] >= 9
    assert "rfc9449" in payload["data"]["not_supported"]


def test_the_conformance_cli_refuses_an_unknown_suite(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["conformance", "--suite", "nope"]) == 1
    assert "unknown" in capsys.readouterr().err


def test_the_suite_registry_covers_the_documented_standards() -> None:
    assert {
        "rfc8693",
        "rfc8707",
        "rfc9700",
        "rfc9728",
        "rfc9068",
        "rfc7636",
        "backends",
        "no-passthrough",
        "widening",
        "rfc9449",
    } <= set(SUITES)
