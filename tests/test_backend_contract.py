"""3.1 - the Backend contract: an opaque SecretValue, capability/health records, error vocabulary."""

from __future__ import annotations

import dataclasses
import json

import pytest

from agentkeys.backends import contract as b


def test_a_secret_value_reveals_only_explicitly() -> None:
    secret = b.SecretValue("plain-text-value")
    assert secret.reveal() == "plain-text-value"
    assert "plain-text-value" not in str(secret)
    assert "plain-text-value" not in repr(secret)
    assert "plain-text-value" not in f"{secret}"
    assert "plain-text-value" not in json.dumps({"v": str(secret)})
    assert secret != "plain-text-value"


def test_a_secret_value_redacts_when_printed_or_formatted() -> None:
    assert repr(b.SecretValue("x")) == "<SecretValue:redacted>"
    assert f"{b.SecretValue('x')}" == "<SecretValue:redacted>"


def test_capability_flags_are_frozen_and_complete() -> None:
    caps = b.BackendCapabilities(
        read_only=True, interactive_unlock=False, file_backed=True, conformance_version="1.0"
    )
    assert caps.conformance_version == "1.0"
    with pytest.raises(dataclasses.FrozenInstanceError):
        caps.read_only = False  # type: ignore[misc]


def test_health_states_are_the_documented_set() -> None:
    for state in ("healthy", "locked", "absent", "ambiguous", "unconfigured"):
        assert b.BackendHealth(state=state, detail="").state == state


def test_the_protocol_declares_the_contract_surface() -> None:
    assert {"backend_id", "kind"} <= set(b.Backend.__annotations__)
    for method in ("capabilities", "open", "close", "resolve", "list", "health"):
        assert method in dir(b.Backend)


def test_the_error_vocabulary_is_closed() -> None:
    for error in (
        b.BackendLocked,
        b.BackendAbsent,
        b.BackendAmbiguous,
        b.BackendUnavailable,
        b.BackendPermissionError,
    ):
        assert issubclass(error, b.BackendError)


def test_the_backend_factory_contract_is_admission_checked() -> None:
    class Unconformant:
        backend_id = "x"
        kind = "x"

        def capabilities(self) -> b.BackendCapabilities:
            return b.BackendCapabilities(True, False, False, "1.0")

    with pytest.raises(b.BackendError, match="resolve"):
        b.admit_backend("x", Unconformant)
