"""3.5 - the fail-closed engine: every backend failure is a denial, never a fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.backends import contract as b
from agentkeys.backends.engine import Denial, FailClosedEngine
from agentkeys.backends.file import FileBackend
from tests.backends_fakes import DictBackend


class ExplodingBackend(DictBackend):
    backend_id = "exploding"

    def __init__(self, error: Exception) -> None:
        super().__init__()
        self._error = error

    def resolve(self, path: str) -> b.SecretValue:
        raise self._error


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (b.BackendLocked("locked"), "backend-locked"),
        (b.BackendAbsent("missing"), "backend-absent"),
        (b.BackendAmbiguous("ambiguous"), "backend-ambiguous"),
        (b.BackendUnavailable("down"), "backend-unavailable"),
        (b.BackendPermissionError("0644"), "backend-permission"),
        (b.BackendError("other"), "backend-unavailable"),
    ],
)
def test_every_backend_failure_maps_to_a_structured_denial(error: Exception, reason: str) -> None:
    engine = FailClosedEngine()
    engine.register(ExplodingBackend(error))
    outcome = engine.resolve("exploding", "slot")
    assert isinstance(outcome, Denial)
    assert outcome.reason == reason
    assert "secret" not in outcome.detail.lower() or "0644" in outcome.detail


def test_a_registered_slot_resolves_through_the_engine() -> None:
    engine = FailClosedEngine()
    engine.register(DictBackend({"slot": "value"}))
    outcome = engine.resolve("dict", "slot")
    assert isinstance(outcome, b.SecretValue)
    assert outcome.reveal() == "value"


def test_an_unknown_backend_is_a_denial_not_a_guess() -> None:
    engine = FailClosedEngine()
    outcome = engine.resolve("nope", "slot")
    assert isinstance(outcome, Denial)
    assert outcome.reason == "unknown-backend"
    assert "nope" in outcome.detail


def test_registering_duplicate_ids_is_ambiguous() -> None:
    engine = FailClosedEngine()
    engine.register(DictBackend())
    with pytest.raises(b.BackendAmbiguous):
        engine.register(DictBackend())


def test_the_engine_never_consults_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENTKEYS_SECRET", "env-value")
    monkeypatch.setenv("AGENTKEYS_FALLBACK", "env-fallback")
    engine = FailClosedEngine()
    engine.register(DictBackend({}))  # an honest backend with no matching slot
    outcome = engine.resolve("dict", "slot")
    assert isinstance(outcome, Denial)
    assert "env-value" not in outcome.detail
    assert "env-fallback" not in outcome.detail
    unknown = engine.resolve("nothing-registered", "slot")
    assert isinstance(unknown, Denial) and unknown.reason == "unknown-backend"


def test_the_fault_matrix_is_deny_or_pending_never_allow() -> None:
    errors = [
        b.BackendLocked("locked"),
        b.BackendAbsent("missing"),
        b.BackendAmbiguous("ambiguous"),
        b.BackendUnavailable("down"),
        b.BackendPermissionError("wide"),
    ]
    allowed = 0
    denied = 0
    for error in errors:
        engine = FailClosedEngine()
        engine.register(ExplodingBackend(error))
        outcome = engine.resolve("exploding", "slot")
        if isinstance(outcome, b.SecretValue):
            allowed += 1
        else:
            denied += 1
    assert (allowed, denied) == (0, len(errors))


def test_health_report_explains_the_effective_setup() -> None:
    engine = FailClosedEngine()
    engine.register(DictBackend())
    report = engine.health_report()
    assert report["dict"].state == "healthy"
    assert "value" not in report["dict"].detail


def test_rotation_without_restart_through_the_engine(tmp_path: Path) -> None:
    credentials = tmp_path / "creds.json"
    credentials.write_text(json.dumps({"slot": "old"}), encoding="utf-8")
    credentials.chmod(0o600)
    backend = FileBackend(credentials)
    backend.open()
    engine = FailClosedEngine()
    engine.register(backend)
    assert engine.resolve("file", "slot").reveal() == "old"  # type: ignore[union-attr]
    credentials.write_text(json.dumps({"slot": "new"}), encoding="utf-8")
    assert engine.resolve("file", "slot").reveal() == "new"  # type: ignore[union-attr]


def test_engine_admits_only_conformant_backends() -> None:
    class Unconformant:
        backend_id = "x"
        kind = "x"

        def capabilities(self) -> b.BackendCapabilities:
            return b.BackendCapabilities(True, False, False, "1.0")

    engine = FailClosedEngine()
    with pytest.raises(b.BackendError, match="resolve"):
        engine.register(Unconformant)
