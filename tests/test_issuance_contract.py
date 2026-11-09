"""2.2 — the `issuance/1.0` contract: bound, TTL-bounded, and free of plaintext fields."""

from __future__ import annotations

import dataclasses
import json

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.issuance import (
    ISSUANCE_VERSION,
    Binding,
    IssuanceDoc,
    IssuanceError,
)
from agentkeys.contracts.reference import ReferenceError


def _ttl() -> dict[str, TtlBound]:
    return {"dev": TtlBound(floor=30, ceiling=900)}


def _doc(**overrides: object) -> IssuanceDoc:
    base: dict[str, object] = {
        "issuance_id": "iss_1",
        "reference_id": "ref_1",
        "session_id": "s1",
        "agent_id": "a1",
        "binding": Binding(audience="api.github.com", tool="gh"),
        "class_": "dev",
        "ttl": 300,
        "issued_at": 1000,
        "expires_at": 1300,
    }
    base.update(overrides)
    return IssuanceDoc(**base)  # type: ignore[arg-type]


def test_a_valid_issuance_round_trips() -> None:
    doc = _doc()
    payload = doc.to_json()
    data = json.loads(payload)
    assert data["issuance"] == ISSUANCE_VERSION
    assert data["binding"] == {"audience": "api.github.com", "tool": "gh"}
    assert IssuanceDoc.from_json(payload) == doc


def test_the_binding_is_the_audience_tool_session_triple() -> None:
    doc = _doc()
    assert doc.binding.audience == "api.github.com"
    assert doc.binding.tool == "gh"
    assert doc.session_id == "s1"
    assert doc.binding_key() == ("api.github.com", "gh", "s1")


@pytest.mark.parametrize("ttl", [29, 901, 0, -1])
def test_ttl_outside_the_class_window_is_rejected(ttl: int) -> None:
    with pytest.raises(IssuanceError, match=r"ttl|TTL"):
        _doc(ttl=ttl, expires_at=1000 + max(ttl, 0)).validate_ttl(_ttl())


def test_ttl_inside_the_class_window_is_accepted() -> None:
    _doc(ttl=30, expires_at=1030).validate_ttl(_ttl())
    _doc(ttl=900, expires_at=1900).validate_ttl(_ttl())


def test_an_unknown_class_has_no_window_and_is_refused() -> None:
    with pytest.raises(IssuanceError, match="class"):
        _doc(class_="staging", ttl=300).validate_ttl(_ttl())


def test_expiry_must_match_issue_time_plus_ttl() -> None:
    with pytest.raises(IssuanceError, match="expires_at"):
        _doc(ttl=300, issued_at=1000, expires_at=9999)


def test_the_document_has_no_plaintext_secret_field() -> None:
    names = {field.name for field in dataclasses.fields(IssuanceDoc)}
    assert "secret" not in names
    assert "token" not in names
    assert "secret_hash" not in names
    assert not any("plaintext" in name or "value" in name for name in names)


def test_a_secret_shaped_value_cannot_be_smuggled_into_a_field() -> None:
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    with pytest.raises(IssuanceError, match="audience"):
        _doc(binding=Binding(audience=secret, tool="gh"))
    with pytest.raises(IssuanceError, match="agent_id"):
        _doc(agent_id=secret)
    with pytest.raises(IssuanceError, match="provenance"):
        _doc(provenance={"decided_by": secret, "decision": "allow"})


def test_provenance_is_optional_and_additive() -> None:
    assert _doc().provenance is None
    doc = _doc(provenance={"decided_by": "agentpolicy", "decision": "allow"})
    assert IssuanceDoc.from_json(doc.to_json()) == doc


def test_unknown_fields_are_ignored() -> None:
    data = json.loads(_doc().to_json())
    data["future"] = 1
    assert IssuanceDoc.from_dict(data) == _doc()


def test_a_secret_shaped_reference_id_is_refused() -> None:
    with pytest.raises((IssuanceError, ReferenceError), match="reference_id"):
        _doc(reference_id="sk-0123456789abcdefghijklmnopqrstuvwxyz")
