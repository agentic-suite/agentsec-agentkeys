"""The Backend contract: one interface, an opaque secret handle, a denial vocabulary (M3, WBS 3.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol

__all__ = [
    "Backend",
    "BackendAbsent",
    "BackendAmbiguous",
    "BackendCapabilities",
    "BackendError",
    "BackendHealth",
    "BackendLocked",
    "BackendPermissionError",
    "BackendUnavailable",
    "HealthState",
    "SecretValue",
    "admit_backend",
    "required_backend_methods",
]

HealthState = Literal["healthy", "locked", "absent", "ambiguous", "unconfigured"]

_MASK = "<SecretValue:redacted>"


class SecretValue:
    """A plaintext secret that refuses to be logged, formatted, serialised, or compared to text."""

    __slots__ = ("_value",)

    def __init__(self, value: str) -> None:
        if not isinstance(value, str):
            raise BackendError("SecretValue requires a string")
        self._value = value

    def reveal(self) -> str:
        """The only way to obtain the plaintext — call it at the moment of use, nothing else."""
        return self._value

    def __repr__(self) -> str:
        return _MASK

    def __str__(self) -> str:
        return _MASK

    def __format__(self, spec: str) -> str:
        return _MASK

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SecretValue):
            return NotImplemented
        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)


class BackendError(Exception):
    """Base class for every backend failure (all fail closed)."""


class BackendLocked(BackendError):
    """The store is locked (keychain locked, unlock in progress). Issuance waits or denies."""


class BackendAbsent(BackendError):
    """The backend or the referenced slot does not exist."""


class BackendAmbiguous(BackendError):
    """More than one candidate matched — refusal, never first-match-wins."""


class BackendUnavailable(BackendError):
    """The backend could not be reached (tool missing, service down)."""


class BackendPermissionError(BackendError):
    """The material is readable by more than the owner (permissions too wide)."""


@dataclass(frozen=True)
class BackendCapabilities:
    """Declared, checkable properties of a backend driver."""

    read_only: bool
    interactive_unlock: bool
    file_backed: bool
    conformance_version: str


@dataclass(frozen=True)
class BackendHealth:
    """Non-secret health of a backend, cheap enough for `doctor`."""

    state: HealthState
    detail: str


class Backend(Protocol):
    """The only way a credential is obtained. `resolve` never falls back."""

    backend_id: str
    kind: str

    def capabilities(self) -> BackendCapabilities: ...

    def open(self) -> None: ...

    def close(self) -> None: ...

    def resolve(self, path: str) -> SecretValue: ...

    def list(self) -> tuple[str, ...]: ...

    def health(self) -> BackendHealth: ...


_REQUIRED_METHODS: tuple[str, ...] = tuple(
    sorted(name for name in dir(Backend) if not name.startswith("_"))
)


def required_backend_methods() -> tuple[str, ...]:
    """The contract surface a backend must expose."""
    return _REQUIRED_METHODS


def admit_backend(backend_id: str, target: Any) -> Backend:
    """Admit a backend by class or instance; refuse an unconformant one, naming what is missing."""
    try:
        instance = target() if callable(target) else target
    except TypeError as exc:
        raise BackendError(f"backend {backend_id} could not be constructed: {exc}") from exc
    missing = [
        method for method in _REQUIRED_METHODS if not callable(getattr(instance, method, None))
    ]
    if missing:
        raise BackendError(
            f"backend {backend_id} is not conformant: missing {', '.join(sorted(missing))}"
        )
    return instance  # type: ignore[no-any-return]
