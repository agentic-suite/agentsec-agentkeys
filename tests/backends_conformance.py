"""The backend conformance suite - the contract's executable form (M3, WBS 3.4).

`run_backend_conformance(factory, expected)` returns findings; an empty list means the driver honours
resolve-at-use, never-log, fail-closed, and capability honesty. Broken drivers must fail it.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

from agentkeys.backends import contract as b

__all__ = ["Finding", "run_backend_conformance"]

Factory = Callable[[str], b.Backend]
_CHECKS: list[Callable[[Factory, str, str, list["Finding"]], None]] = []


@dataclass(frozen=True)
class Finding:
    """One conformance failure: the check that failed and why."""

    check: str
    detail: str


def check(
    function: Callable[[Factory, str, str, list[Finding]], None],
) -> Callable[[Factory, str, str, list[Finding]], None]:
    _CHECKS.append(function)
    return function


def _expect(condition: bool, findings: list[Finding], name: str, detail: str) -> None:
    if not condition:
        findings.append(Finding(check=name, detail=detail))


@check
def capabilities_are_declared(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("capabilities")
    backend.open()
    try:
        caps = backend.capabilities()
        _expect(
            isinstance(caps, b.BackendCapabilities),
            findings,
            "capabilities",
            "capabilities() must return BackendCapabilities",
        )
        _expect(
            caps.conformance_version == "1.0",
            findings,
            "capabilities",
            f"unexpected conformance_version: {caps.conformance_version!r}",
        )
    finally:
        backend.close()


@check
def resolve_returns_an_opaque_secret(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("resolve")
    backend.open()
    try:
        secret = backend.resolve(slot)
        _expect(
            isinstance(secret, b.SecretValue),
            findings,
            "resolve",
            f"resolve returned {type(secret).__name__}, not SecretValue",
        )
        if isinstance(secret, b.SecretValue):
            _expect(
                value not in repr(secret) and value not in str(secret),
                findings,
                "resolve",
                "the secret value was observable via repr/str",
            )
            revealed = secret.reveal()
            _expect(
                revealed == value, findings, "resolve", "revealed value does not match the slot"
            )
    finally:
        backend.close()


@check
def an_unknown_slot_fails_closed(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("unknown-slot")
    backend.open()
    try:
        backend.resolve("__no_such_slot__")
        findings.append(
            Finding("fail-closed", "resolving an unknown slot did not raise (a fallback exists)")
        )
    except b.BackendError:
        pass
    except Exception as exc:  # noqa: BLE001 - any other exception is a contract violation
        findings.append(Finding("fail-closed", f"unknown slot raised {exc!r}, not BackendError"))
    finally:
        backend.close()


@check
def listing_never_leaks_a_value(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("list")
    backend.open()
    try:
        actual = backend.resolve(slot).reveal()
        try:
            listed = backend.list()
        except b.BackendUnavailable as exc:
            _expect(
                "enumerat" in str(exc).lower(),
                findings,
                "list",
                "an unsupported enumeration must say so",
            )
            return
        _expect(
            isinstance(listed, tuple), findings, "list", "list() must return a tuple of paths"
        )
        _expect(
            all(isinstance(entry, str) for entry in listed),
            findings,
            "list",
            "list() must return strings",
        )
        _expect(actual not in listed, findings, "list", "list() leaked the resolved value")
        _expect(value not in listed, findings, "list", "list() leaked a secret value")
    finally:
        backend.close()


@check
def health_is_valid_and_non_secret(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("health")
    backend.open()
    try:
        health = backend.health()
        _expect(
            health.state in {"healthy", "locked", "absent", "ambiguous", "unconfigured"},
            findings,
            "health",
            f"invalid health state: {health.state!r}",
        )
        _expect(value not in health.detail, findings, "health", "health detail leaked a value")
    finally:
        backend.close()


@check
def file_backed_drivers_enforce_owner_only_permissions(
    factory: Factory, slot: str, value: str, findings: list[Finding]
) -> None:
    backend = factory("perms")
    backend.open()
    try:
        caps = backend.capabilities()
        if not caps.file_backed:
            return
        path = getattr(backend, "path", None)
        _expect(path is not None, findings, "permissions", "a file backend must expose its path")
        if path is not None:
            mode = os.stat(path).st_mode & 0o777
            _expect(
                mode == 0o600,
                findings,
                "permissions",
                f"credential file mode is {mode:04o}, want 0600",
            )
    finally:
        backend.close()


@check
def capabilities_are_honest_about_file_backing(factory: Factory, slot: str, value: str, findings: list[Finding]) -> None:
    backend = factory("honesty")
    backend.open()
    try:
        caps = backend.capabilities()
        has_path = getattr(backend, "path", None) is not None
        _expect(
            caps.file_backed == has_path,
            findings,
            "capabilities",
            "file_backed must match whether the backend reads a file",
        )
    finally:
        backend.close()


def run_backend_conformance(factory: Factory, slot: str, value: str) -> list[Finding]:
    """Run every check against bounded fresh backends; return the findings."""
    findings: list[Finding] = []
    for function in _CHECKS:
        key = function.__name__

        def bound(_key: str = key) -> b.Backend:
            return factory(_key)

        try:
            function(bound, slot, value, findings)
        except Exception as exc:  # a crashing backend is a finding, not a test error
            findings.append(Finding(check=function.__name__, detail=f"raised {exc!r}"))
    return findings