"""2.3 - the reference registry: registration, strict grammar, loud unknown-key refusal."""

from __future__ import annotations

import dataclasses

import pytest

from agentkeys.contracts.reference import ReferenceDoc, ReferenceError
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.store.memory import MemoryStore


@pytest.fixture
def registry() -> ReferenceRegistry:
    store = MemoryStore()
    store.open()
    return ReferenceRegistry(store)


def _doc(
    backend: str = "keychain", path: str = "agentkeys/dev/token", label: str = "dev token"
) -> ReferenceDoc:
    return ReferenceDoc(reference_id="ref_1", backend=backend, path=path, class_="dev", label=label)


def test_registration_is_idempotent(registry: ReferenceRegistry) -> None:
    first = registry.register(_doc())
    assert registry.register(_doc()) == first
    assert registry.get("akref:keychain/agentkeys/dev/token") == first
    assert registry.list() == (first,)


def test_a_conflicting_registration_is_refused(registry: ReferenceRegistry) -> None:
    registry.register(_doc())
    conflicting = dataclasses.replace(_doc(), class_="prod")
    with pytest.raises(ReferenceError, match="conflict"):
        registry.register(conflicting)


def test_an_unknown_key_is_rejected_with_the_shape_named(registry: ReferenceRegistry) -> None:
    with pytest.raises(UnknownReference, match="akref:"):
        registry.get("akref:keychain/agentkeys/dev/missing")


def test_a_malformed_key_is_a_grammar_error(registry: ReferenceRegistry) -> None:
    with pytest.raises(ReferenceError, match="malformed"):
        registry.get("keychain/agentkeys/dev/token")


def test_lookup_by_document_and_by_key_agree(registry: ReferenceRegistry) -> None:
    doc = registry.register(_doc())
    assert registry.get("akref:keychain/agentkeys/dev/token") == doc
    assert registry.get(reference_id="ref_1") == doc


def test_a_missing_reference_id_is_rejected(registry: ReferenceRegistry) -> None:
    with pytest.raises(UnknownReference, match="ref_nope"):
        registry.get(reference_id="ref_nope")


def test_the_registry_never_returns_a_value_only_a_document(registry: ReferenceRegistry) -> None:
    registry.register(_doc())
    assert all(isinstance(item, ReferenceDoc) for item in registry.list())
    assert not hasattr(registry, "get_secret")
    assert not hasattr(registry, "resolve_value")


def test_a_secret_shaped_document_cannot_be_registered(registry: ReferenceRegistry) -> None:
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    with pytest.raises(ReferenceError, match="label"):
        _doc(label=secret)
