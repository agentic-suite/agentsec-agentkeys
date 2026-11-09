"""3.4 - one conformance suite for every backend; deliberately broken ones must fail it."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from agentkeys.backends import contract as b
from agentkeys.backends.file import FileBackend
from agentkeys.backends.keychain import CommandResult, KeychainBackend
from tests.backends_conformance import run_backend_conformance
from tests.backends_fakes import (
    DictBackend,
    FallbackBackend,
    LeakyBackend,
    LockedBackend,
    ValueListingBackend,
)

SLOT = "slot"
VALUE = "conf-value"


def _dict_factory(key: str) -> b.Backend:
    return DictBackend({SLOT: VALUE})


def _file_factory(tmp_path: Path) -> Callable[[str], b.Backend]:
    def factory(key: str) -> b.Backend:
        path = tmp_path / f"{key}.json"
        path.write_text(json.dumps({SLOT: VALUE}), encoding="utf-8")
        path.chmod(0o600)
        return FileBackend(path)

    return factory


def _keychain_factory() -> Callable[[str], b.Backend]:
    class Runner:
        """Emulates `security`: the slot resolves, an unknown slot is not found."""

        def run(self, argv: list[str]) -> CommandResult:
            account = argv[argv.index("-a") + 1]
            if account == SLOT:
                return CommandResult(0, f"{VALUE}\n", "")
            return CommandResult(44, "", "The specified item could not be found")

    def factory(key: str) -> b.Backend:
        return KeychainBackend(service="agentkeys", runner=Runner(), platform="darwin")

    return factory


@pytest.fixture(params=["dict", "file", "keychain"])
def good_factory(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[str], b.Backend]:
    if request.param == "dict":
        return _dict_factory
    if request.param == "file":
        return _file_factory(tmp_path)
    return _keychain_factory()


def test_real_backends_conform(good_factory: Callable[[str], b.Backend]) -> None:
    findings = run_backend_conformance(good_factory, SLOT, VALUE)
    assert findings == [], findings


@pytest.mark.parametrize(
    ("fake", "expected_check"),
    [
        (LeakyBackend, "resolve"),
        (FallbackBackend, "fail-closed"),
        (ValueListingBackend, "list"),
    ],
)
def test_broken_backends_fail_the_suite(fake: type[DictBackend], expected_check: str) -> None:
    findings = run_backend_conformance(lambda key: fake({SLOT: VALUE}), SLOT, VALUE)
    assert findings, f"{fake.__name__} passed a suite it must fail"
    assert expected_check in {finding.check for finding in findings}


def test_a_locked_backend_denies_and_cannot_conform() -> None:
    # A locked backend cannot serve a resolution; it denies (and the suite reports that honestly).
    with pytest.raises(b.BackendLocked):
        LockedBackend().resolve(SLOT)
    findings = run_backend_conformance(lambda key: LockedBackend(), SLOT, VALUE)
    assert "resolve_returns_an_opaque_secret" in {finding.check for finding in findings}


def test_a_backend_without_resolve_is_refused_by_admission() -> None:
    class NoResolve:
        backend_id = "no-resolve"
        kind = "x"

        def capabilities(self) -> b.BackendCapabilities:
            return b.BackendCapabilities(True, False, False, "1.0")

    with pytest.raises(b.BackendError, match="resolve"):
        b.admit_backend("no-resolve", NoResolve)
