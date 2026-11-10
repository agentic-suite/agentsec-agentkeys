"""2.1 — the `akref/1.0` reference: opaque, loggable, and never a secret."""

from __future__ import annotations

import json

import pytest

from agentkeys.contracts.reference import (
    AKREF_VERSION,
    ReferenceDoc,
    ReferenceError,
    parse_reference_key,
)


def _doc(**overrides: object) -> ReferenceDoc:
    base: dict[str, object] = {
        "reference_id": "ref_1",
        "backend": "keychain",
        "path": "agentkeys/dev/token",
        "class_": "dev",
    }
    base.update(overrides)
    return ReferenceDoc(**base)  # type: ignore[arg-type]


def test_a_valid_reference_round_trips_deterministically() -> None:
    doc = _doc(scope_hint="repo:read", label="dev token")
    payload = doc.to_json()
    assert json.loads(payload)["akref"] == AKREF_VERSION
    assert ReferenceDoc.from_json(payload) == doc
    other = _doc(scope_hint="repo:read", label="dev token")
    assert json.loads(payload) == json.loads(other.to_json())


def test_unknown_fields_are_ignored_additive_compat() -> None:
    data = json.loads(_doc().to_json())
    data["future_field"] = {"anything": 1}
    assert ReferenceDoc.from_dict(data) == _doc()


def test_the_class_enum_is_enforced() -> None:
    assert _doc(class_="prod").class_ == "prod"
    with pytest.raises(ReferenceError, match="class"):
        _doc(class_="secret")


@pytest.mark.parametrize("field", ["reference_id", "backend", "path"])
def test_required_fields_must_be_non_empty(field: str) -> None:
    with pytest.raises(ReferenceError, match=field):
        _doc(**{field: ""})


@pytest.mark.parametrize(
    "secret",
    [
        "sk-0123456789abcdefghijklmnopqrstuvwxyz",
        "ghp_0123456789abcdefghijklmnopqrstuvwxyz",
        "AKIAIOSFODNN7EXAMPLE",
        "-----BEGIN RSA PRIVATE KEY-----",
    ],
)
def test_a_secret_shaped_value_is_rejected_and_named(secret: str) -> None:
    with pytest.raises(ReferenceError, match="label"):
        _doc(label=secret)
    with pytest.raises(ReferenceError, match="path"):
        _doc(path=secret)
    with pytest.raises(ReferenceError, match="scope_hint"):
        _doc(scope_hint=secret)


def test_the_serialised_document_contains_no_secret_material() -> None:
    doc = _doc(scope_hint="repo:read", label="prod-ish token")
    text = doc.to_json()
    assert "sk-" not in text and "BEGIN" not in text


def test_malformed_json_is_refused() -> None:
    with pytest.raises(ReferenceError, match="JSON"):
        ReferenceDoc.from_json("{not json")


def test_wrong_contract_version_is_refused() -> None:
    with pytest.raises(ReferenceError, match="akref"):
        ReferenceDoc.from_dict({"akref": "9.9"})


@pytest.mark.parametrize(
    ("key", "backend", "path"),
    [
        ("akref:keychain/agentkeys/dev/token", "keychain", "agentkeys/dev/token"),
        ("akref:file/a", "file", "a"),
    ],
)
def test_the_reference_key_grammar_accepts_valid_keys(key: str, backend: str, path: str) -> None:
    assert parse_reference_key(key) == (backend, path)


@pytest.mark.parametrize(
    "key",
    [
        "keychain/agentkeys/dev/token",  # no scheme
        "akref:",
        "akref:Keychain/x",  # uppercase backend
        "akref:keychain/../escape",
        "akref:keychain/a b",  # space
        "akref:keychain/",
    ],
)
def test_the_reference_key_grammar_refuses_malformed_keys(key: str) -> None:
    with pytest.raises(ReferenceError):
        parse_reference_key(key)


def test_parsing_errors_are_typed() -> None:
    with pytest.raises(ReferenceError, match="object"):
        ReferenceDoc.from_json("[]")
    with pytest.raises(ReferenceError, match="missing"):
        ReferenceDoc.from_dict({"akref": "1.0", "reference_id": "r"})
    with pytest.raises(ReferenceError, match="version"):
        _doc(akref="9.9")
