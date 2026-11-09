"""3.2 - the keychain driver: unlock-per-resolve, never a value in list/health, no caching."""

from __future__ import annotations

import pytest

from agentkeys.backends import contract as b
from agentkeys.backends.keychain import CommandResult, KeychainBackend


class FakeRunner:
    """An injectable command runner; the real keychain is never touched by tests."""

    def __init__(self, responses: list[CommandResult]) -> None:
        self.responses = responses
        self.calls: list[list[str]] = []

    def run(self, argv: list[str]) -> CommandResult:
        self.calls.append(argv)
        return self.responses.pop(0)


def _ok(value: str = "s3cr3t-value") -> CommandResult:
    return CommandResult(returncode=0, stdout=f"{value}\n", stderr="")


def _backend(platform: str, responses: list[CommandResult]) -> tuple[KeychainBackend, FakeRunner]:
    runner = FakeRunner(responses)
    return KeychainBackend(service="agentkeys", runner=runner, platform=platform), runner


def test_resolve_returns_an_opaque_secret_on_macos() -> None:
    backend, runner = _backend("darwin", [_ok()])
    backend.open()
    secret = backend.resolve("agentkeys/dev/token")
    assert secret.reveal() == "s3cr3t-value"
    assert "s3cr3t-value" not in repr(secret)
    argv = runner.calls[0]
    assert argv[:3] == ["security", "find-generic-password", "-w"]
    assert "-s" in argv and "agentkeys" in argv and "-a" in argv


def test_resolve_uses_secret_tool_on_linux() -> None:
    backend, runner = _backend("linux", [_ok("linux-secret")])
    backend.open()
    assert backend.resolve("agentkeys/dev/token").reveal() == "linux-secret"
    assert runner.calls[0][0] == "secret-tool"
    assert "lookup" in runner.calls[0]


def test_resolve_does_not_cache_so_rotation_is_picked_up() -> None:
    backend, runner = _backend("darwin", [_ok("old"), _ok("new")])
    backend.open()
    assert backend.resolve("p").reveal() == "old"
    assert backend.resolve("p").reveal() == "new"
    assert len(runner.calls) == 2


@pytest.mark.parametrize(
    ("result", "error"),
    [
        (CommandResult(44, "", "The specified item could not be found"), b.BackendAbsent),
        (CommandResult(1, "", "User interaction is not allowed."), b.BackendLocked),
        (CommandResult(1, "", "keychain is locked"), b.BackendLocked),
        (CommandResult(2, "", "unexpected failure"), b.BackendUnavailable),
        (CommandResult(0, "\n", ""), b.BackendAbsent),
    ],
)
def test_failures_map_to_the_denial_vocabulary(result: CommandResult, error: type) -> None:
    backend, _ = _backend("darwin", [result])
    backend.open()
    with pytest.raises(error):
        backend.resolve("p")


def test_an_unsupported_platform_is_unavailable() -> None:
    backend, _ = _backend("win32", [])
    with pytest.raises(b.BackendUnavailable, match="platform"):
        backend.open()


def test_list_never_returns_a_value_and_may_report_a_limitation() -> None:
    backend, _ = _backend("darwin", [])
    backend.open()
    try:
        listed = backend.list()
    except b.BackendUnavailable as exc:
        assert "enumerat" in str(exc).lower()
        return
    assert listed == () or all(" " not in entry for entry in listed)


def test_health_is_non_secret_and_valid() -> None:
    backend, _ = _backend("darwin", [])
    backend.open()
    health = backend.health()
    assert health.state in {"healthy", "locked", "absent", "ambiguous", "unconfigured"}
    assert "s3cr3t" not in health.detail


def test_capabilities_declare_the_kind_and_conformance_version() -> None:
    backend, _ = _backend("darwin", [])
    caps = backend.capabilities()
    assert backend.kind == "keychain"
    assert caps.conformance_version == "1.0"
    assert caps.interactive_unlock is True
    assert caps.file_backed is False


def test_a_missing_keychain_tool_is_unavailable() -> None:
    class MissingRunner:
        def run(self, argv: list[str]) -> CommandResult:
            raise FileNotFoundError("security")

    backend = KeychainBackend(service="agentkeys", runner=MissingRunner(), platform="darwin")
    with pytest.raises(b.BackendUnavailable):
        backend.resolve("p")


def test_a_closed_or_empty_path_is_refused() -> None:
    backend, _ = _backend("darwin", [])
    with pytest.raises(b.BackendUnavailable):
        backend.resolve("p")
    backend.open()
    with pytest.raises(b.BackendAbsent, match="empty"):
        backend.resolve("")


def test_list_reports_the_enumeration_limitation() -> None:
    backend, _ = _backend("darwin", [])
    backend.open()
    with pytest.raises(b.BackendUnavailable, match="enumerat"):
        backend.list()


def test_health_is_unconfigured_before_open_and_after_close() -> None:
    backend, _ = _backend("darwin", [])
    assert backend.health().state == "unconfigured"
    backend.open()
    assert backend.health().state == "healthy"
    backend.close()
    assert backend.health().state == "unconfigured"


def test_an_unsupported_platform_reports_unconfigured_health() -> None:
    backend, _ = _backend("win32", [])
    assert backend.health().state == "unconfigured"


def test_a_missing_tool_surfaces_as_unavailable() -> None:
    class MissingRunner:
        def run(self, argv: list[str]) -> CommandResult:
            raise FileNotFoundError("security")

    backend = KeychainBackend(service="agentkeys", runner=MissingRunner(), platform="darwin")
    backend.open()
    with pytest.raises(b.BackendUnavailable, match="not available"):
        backend.resolve("p")
