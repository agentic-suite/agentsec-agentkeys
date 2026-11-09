"""The OS-keychain backend: unlock-per-resolve, never a cached or written plaintext
(M3, WBS 3.2)."""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from typing import Protocol

from agentkeys.backends.contract import (
    BackendAbsent,
    BackendCapabilities,
    BackendHealth,
    BackendLocked,
    BackendUnavailable,
    SecretValue,
)

__all__ = ["CommandResult", "CommandRunner", "KeychainBackend", "SubprocessRunner"]

_SUPPORTED = ("darwin", "linux")
_LOCKED_MARKERS = ("locked", "interaction not allowed", "user interaction is not allowed")
_ABSENT_MARKERS = ("could not be found", "the specified item could not be found", "not found")


@dataclass(frozen=True)
class CommandResult:
    """The outcome of one backend command (never contains a secret we log)."""

    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    """Runs one command; injectable so tests never touch a real keychain."""

    def run(self, argv: list[str]) -> CommandResult: ...


class SubprocessRunner:
    """The production runner (macOS `security`, Linux `secret-tool`)."""

    def run(self, argv: list[str]) -> CommandResult:
        try:
            # Fixed argv, no shell; the tool and slot come from trusted config, not agent input.
            completed = subprocess.run(  # noqa: S603
                argv, capture_output=True, text=True, check=False
            )
        except FileNotFoundError as exc:
            raise BackendUnavailable(f"keychain tool not available: {argv[0]}") from exc
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)


class KeychainBackend:
    """Resolves slots from the OS keychain; a failure is always a denial."""

    backend_id = "keychain"
    kind = "keychain"

    def __init__(
        self,
        *,
        service: str = "agentkeys",
        runner: CommandRunner | None = None,
        platform: str | None = None,
    ) -> None:
        self._service = service
        self._runner: CommandRunner = SubprocessRunner() if runner is None else runner
        self._platform = platform or sys.platform
        self._open = False

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            read_only=False,
            interactive_unlock=True,
            file_backed=False,
            conformance_version="1.0",
        )

    def open(self) -> None:
        if not self._platform.startswith(_SUPPORTED):
            raise BackendUnavailable(
                f"unsupported platform for the keychain backend: {self._platform}"
            )
        self._open = True

    def close(self) -> None:
        self._open = False

    def _argv(self, path: str) -> list[str]:
        if self._platform == "darwin":
            return [
                "security",
                "find-generic-password",
                "-w",
                "-s",
                self._service,
                "-a",
                path,
            ]
        return ["secret-tool", "lookup", "service", self._service, "account", path]

    def resolve(self, path: str) -> SecretValue:
        if not self._open:
            raise BackendUnavailable("keychain backend is not open")
        if not path:
            raise BackendAbsent("empty keychain path")
        try:
            result = self._runner.run(self._argv(path))
        except FileNotFoundError as exc:
            raise BackendUnavailable(f"keychain tool not available: {self._argv(path)[0]}") from exc
        if result.returncode == 0:
            value = result.stdout.strip("\n")
            if not value:
                raise BackendAbsent(f"empty keychain entry for path: {path}")
            return SecretValue(value)
        lowered = result.stderr.lower()
        if any(marker in lowered for marker in _LOCKED_MARKERS):
            raise BackendLocked(f"keychain is locked for path: {path}")
        if any(marker in lowered for marker in _ABSENT_MARKERS) or result.returncode == 44:
            raise BackendAbsent(f"keychain entry not found for path: {path}")
        raise BackendUnavailable(f"keychain lookup failed for path: {path}")

    def list(self) -> tuple[str, ...]:
        raise BackendUnavailable(
            "the keychain driver cannot enumerate slots portably; use references, not listing"
        )

    def health(self) -> BackendHealth:
        if not self._platform.startswith(_SUPPORTED):
            return BackendHealth(
                state="unconfigured", detail=f"unsupported platform: {self._platform}"
            )
        if not self._open:
            return BackendHealth(state="unconfigured", detail="not open")
        return BackendHealth(state="healthy", detail=f"service={self._service}")
