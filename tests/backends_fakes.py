"""Deliberately broken backends: the conformance suite must report a finding for each (WBS 3.4)."""

from __future__ import annotations

import os

from agentkeys.backends.contract import (
    BackendAbsent,
    BackendCapabilities,
    BackendError,
    BackendHealth,
    BackendLocked,
    SecretValue,
)

__all__ = ["DictBackend", "FallbackBackend", "LeakyBackend", "LockedBackend", "ValueListingBackend"]


class DictBackend:
    """A conformant in-memory backend used as the suite's baseline."""

    backend_id = "dict"
    kind = "dict"

    def __init__(self, entries: dict[str, str] | None = None, *, locked: bool = False) -> None:
        self.entries = {"slot": "value"} if entries is None else entries
        self.locked = locked
        self._open = False

    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(
            read_only=True,
            interactive_unlock=False,
            file_backed=False,
            conformance_version="1.0",
        )

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def resolve(self, path: str) -> SecretValue:
        if self.locked:
            raise BackendLocked(f"locked: {path}")
        if path not in self.entries:
            raise BackendAbsent(f"missing: {path}")
        return SecretValue(self.entries[path])

    def list(self) -> tuple[str, ...]:
        return tuple(sorted(self.entries))

    def health(self) -> BackendHealth:
        return BackendHealth(
            state="locked" if self.locked else "healthy", detail=f"entries={len(self.entries)}"
        )


class LockedBackend(DictBackend):
    """Always locked: the suite must see a denial, never a value."""

    def __init__(self) -> None:
        super().__init__(locked=True)


class LeakyBackend(DictBackend):
    """Returns a bare string instead of a SecretValue."""

    def resolve(self, path: str) -> SecretValue:
        return super().resolve(path).reveal()  # type: ignore[return-value]


class FallbackBackend(DictBackend):
    """Falls back to an environment variable instead of failing closed."""

    def resolve(self, path: str) -> SecretValue:
        try:
            return super().resolve(path)
        except BackendError:
            return SecretValue(os.environ.get("AGENTKEYS_FALLBACK", "env-fallback"))


class ValueListingBackend(DictBackend):
    """Leaks values through `list()`."""

    def list(self) -> tuple[str, ...]:
        return tuple(sorted(self.entries.values()))