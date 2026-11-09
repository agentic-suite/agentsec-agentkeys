"""The fail-closed engine: a backend failure is a structured denial, never a fallback (M3, WBS 3.5)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentkeys.backends.contract import (
    Backend,
    BackendAbsent,
    BackendAmbiguous,
    BackendError,
    BackendHealth,
    BackendLocked,
    BackendPermissionError,
    SecretValue,
    admit_backend,
)

__all__ = ["Denial", "DenialReason", "FailClosedEngine"]

DenialReason = Literal[
    "backend-locked",
    "backend-absent",
    "backend-ambiguous",
    "backend-unavailable",
    "backend-permission",
    "unknown-backend",
]


@dataclass(frozen=True)
class Denial:
    """A fail-closed denial: the reason and where it happened, never a value."""

    reason: DenialReason
    detail: str


class FailClosedEngine:
    """Resolves through exactly one registered backend, or denies. There is no fallback path."""

    def __init__(self) -> None:
        self._backends: dict[str, Backend] = {}

    def register(self, backend: object) -> Backend:
        """Admit and register a backend; a duplicate id or an unconformant backend is refused."""
        candidate = backend if isinstance(backend, str) else getattr(backend, "backend_id", None)
        backend_id = candidate if isinstance(candidate, str) else "unnamed"
        admitted = admit_backend(backend_id, backend)
        if admitted.backend_id in self._backends:
            raise BackendAmbiguous(f"duplicate backend registration: {admitted.backend_id}")
        self._backends[admitted.backend_id] = admitted
        return admitted

    def backends(self) -> tuple[str, ...]:
        return tuple(sorted(self._backends))

    def resolve(self, backend_id: str, path: str) -> SecretValue | Denial:
        """The single resolution path. Any failure is a denial with a named reason."""
        backend = self._backends.get(backend_id)
        if backend is None:
            return Denial(
                reason="unknown-backend",
                detail=f"no backend registered with id: {backend_id}",
            )
        try:
            return backend.resolve(path)
        except BackendLocked:
            return Denial("backend-locked", f"backend locked: {backend_id}/{path}")
        except BackendPermissionError:
            return Denial(
                "backend-permission",
                f"backend material is readable beyond its owner: {backend_id}/{path}",
            )
        except BackendAbsent:
            return Denial("backend-absent", f"backend entry absent: {backend_id}/{path}")
        except BackendAmbiguous:
            return Denial("backend-ambiguous", f"ambiguous backend result: {backend_id}/{path}")
        except BackendError:
            return Denial(
                "backend-unavailable",
                f"backend unavailable or entry absent: {backend_id}/{path}",
            )

    def health_report(self) -> dict[str, BackendHealth]:
        """Per-backend health for `doctor`; never a value."""
        report: dict[str, BackendHealth] = {}
        for backend_id, backend in sorted(self._backends.items()):
            try:
                report[backend_id] = backend.health()
            except BackendError as exc:
                report[backend_id] = BackendHealth(
                    state="unconfigured", detail=f"health check failed: {exc.__class__.__name__}"
                )
        return report