"""Backends: one contract, keychain + file drivers, the fail-closed engine (M3)."""

from __future__ import annotations

from agentkeys.backends.contract import (
    Backend,
    BackendAbsent,
    BackendAmbiguous,
    BackendCapabilities,
    BackendError,
    BackendHealth,
    BackendLocked,
    BackendPermissionError,
    BackendUnavailable,
    HealthState,
    SecretValue,
    admit_backend,
    required_backend_methods,
)

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
