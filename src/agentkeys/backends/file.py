"""The credential-file backend: 0600 enforced, loud warning, never a value in list (M3, WBS 3.3)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from agentkeys.backends.contract import (
    BackendAbsent,
    BackendAmbiguous,
    BackendCapabilities,
    BackendHealth,
    BackendPermissionError,
    BackendUnavailable,
    SecretValue,
)

__all__ = ["FileBackend"]

_REQUIRED_MODE = 0o600
_WARNING = "warning: credential-file backend in use; prefer the OS keychain"


class FileBackend:
    """A `0600` credential file (JSON object or `NAME=value` lines). Read-only, fail closed."""

    backend_id = "file"
    kind = "file"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._entries: dict[str, str] = {}
        self._open = False

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            read_only=True,
            interactive_unlock=False,
            file_backed=True,
            conformance_version="1.0",
        )

    def open(self) -> None:
        if not self.path.exists():
            raise BackendAbsent(f"credential file missing: {self.path}")
        self._entries = self._load()
        self._open = True

    def close(self) -> None:
        self._entries = {}
        self._open = False

    def _check_permissions(self) -> None:
        mode = self.path.stat().st_mode & 0o777
        if mode & 0o177:
            raise BackendPermissionError(
                f"credential file permission must be 0600, found {mode:04o}: {self.path}"
            )

    def _load(self) -> dict[str, str]:
        self._check_permissions()
        try:
            text = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise BackendUnavailable(
                f"credential file unreadable: {exc.__class__.__name__}"
            ) from exc
        stripped = text.strip()
        if not stripped:
            return {}
        if stripped.startswith(("{", "[")):
            try:
                data = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise BackendAmbiguous(f"malformed credential file: {exc.msg}") from exc
            if not isinstance(data, dict):
                raise BackendAmbiguous("credential JSON must be an object of name → value")
            return {str(key): str(value) for key, value in data.items()}
        return self._load_pairs(stripped)

    @staticmethod
    def _load_pairs(text: str) -> dict[str, str]:
        entries: dict[str, str] = {}
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            name = name.strip()
            if not separator or not name:
                raise BackendAmbiguous(f"malformed credential line: {name or '<empty>'}")
            if name in entries:
                raise BackendAmbiguous(f"duplicate credential entry: {name}")
            entries[name] = value.strip()
        return entries

    def resolve(self, path: str) -> SecretValue:
        if not self._open:
            raise BackendUnavailable("credential-file backend is not open")
        self._entries = (
            self._load()
        )  # re-read every resolve: rotation is picked up, nothing is cached
        if path not in self._entries:
            raise BackendAbsent(f"missing credential entry: {path}")
        value = self._entries[path]
        if not value:
            raise BackendAbsent(f"empty credential entry: {path}")
        return SecretValue(value)

    def list(self) -> tuple[str, ...]:
        if not self._open:
            raise BackendUnavailable("credential-file backend is not open")
        self._entries = self._load()
        return tuple(sorted(self._entries))

    def health(self) -> BackendHealth:
        if not self.path.exists():
            return BackendHealth(state="absent", detail=f"missing: {self.path}")
        if not self._open:
            return BackendHealth(state="unconfigured", detail="not open")
        return BackendHealth(state="healthy", detail=_WARNING)


def chmod_owner_only(path: str | Path) -> None:
    """Set a credential file to `0600` (used by `migrate` in M8)."""
    os.chmod(path, _REQUIRED_MODE)
