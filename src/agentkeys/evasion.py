"""Secret-evasion detection: raw reads outside the broker are high-severity events (M9, R7).

Honesty rule (R7/E10): `enforce` blocks only where an enforcer composes; everywhere else the
attempt is recorded and the gap is explicitly named. A monitor-class detector never claims a block.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from pathlib import PurePath

from agentkeys.events import build_event
from agentkeys.store.contract import BrokerStore, LedgerEvent

__all__ = [
    "EVASION_CLASSES",
    "AccessAttempt",
    "EvasionDetector",
    "EvasionMonitor",
    "EvasionVerdict",
    "classify_path",
    "evasion_event",
]

EVASION_CLASSES: tuple[str, ...] = (
    "dotenv",
    "cloud-credential",
    "keychain",
    "ssh-key",
    "env-export",
)

_MODES = ("monitor", "enforce")
Enforcer = Callable[["AccessAttempt"], bool]


@dataclass(frozen=True)
class AccessAttempt:
    """One raw-credential access outside the broker (metadata only, no secret value)."""

    path: str
    principal: str
    session_id: str | None = None
    agent_id: str | None = None
    operation: str = "read"


@dataclass(frozen=True)
class EvasionVerdict:
    """The detector's decision: detected, class, blocked, and whether a gap is named."""

    detected: bool
    class_: str | None
    severity: str | None
    blocked: bool
    gap_named: bool
    reason: str | None


def classify_path(path: str) -> str | None:
    """Classify a path into the evasion vocabulary; an unrelated path is `None`."""
    lowered = path.lower()
    name = PurePath(lowered).name
    if name == ".env" or name.startswith(".env.") or name.endswith(".env"):
        return "dotenv"
    if (
        "/.aws/credentials" in lowered
        or name == "application_default_credentials.json"
        or "/.azure/" in lowered
    ):
        return "cloud-credential"
    if name in {"login.keychain", "login.keychain-db"} or lowered.endswith(".keychain-db"):
        return "keychain"
    if "/keyrings/" in lowered:
        return "keychain"
    if name in {"id_rsa", "id_ed25519", "id_ecdsa", "id_dsa"} or name.endswith((".pem", ".key")):
        return "ssh-key"
    if name.startswith(("agentkeys_", "agentkeys-")):
        return "env-export"
    return None


class EvasionDetector:
    """Detects raw-credential reads; enforces only when a real enforcer is composed."""

    def __init__(self, *, mode: str = "monitor", enforcer: Enforcer | None = None) -> None:
        if mode not in _MODES:
            raise ValueError(f"unknown evasion mode: {mode!r} (expected monitor or enforce)")
        self._mode = mode
        self._enforcer = enforcer

    def observe(self, attempt: AccessAttempt) -> EvasionVerdict:
        klass = classify_path(attempt.path)
        if klass is None:
            return EvasionVerdict(False, None, None, False, False, None)
        if self._mode == "monitor":
            return EvasionVerdict(
                True,
                klass,
                "high",
                False,
                False,
                f"monitor-only: {klass} read outside the broker",
            )
        if self._enforcer is None:
            return EvasionVerdict(
                True,
                klass,
                "high",
                False,
                True,
                f"gap: no enforcer covers {klass} reads",
            )
        try:
            blocked = bool(self._enforcer(attempt))
        except Exception:  # an enforcer failure is a gap, never a fabricated block
            blocked = False
        reason = (
            f"blocked: {klass} read outside the broker"
            if blocked
            else f"gap: the enforcer declined the {klass} read"
        )
        return EvasionVerdict(True, klass, "high", blocked, not blocked, reason)


def evasion_event(
    verdict: EvasionVerdict,
    attempt: AccessAttempt,
    *,
    occurred_at: int = 0,
    monotonic_ms: int = 0,
) -> LedgerEvent:
    """The `evasion-detected` evidence: class + path + attribution, never a value."""
    return build_event(
        "evasion-detected",
        occurred_at=occurred_at,
        monotonic_ms=monotonic_ms,
        session_id=attempt.session_id,
        agent_id=attempt.agent_id,
        principal=attempt.principal,
        reason=f"{verdict.class_}: {attempt.path}; {verdict.reason}",
        severity="high",
    )


class EvasionMonitor:
    """Runs the detector and records one high-severity event per detected attempt."""

    def __init__(
        self,
        store: BrokerStore,
        detector: EvasionDetector,
        *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._detector = detector
        self._clock = clock or (lambda: int(time.time()))

    def record(
        self,
        attempt: AccessAttempt,
        *,
        session_id: str | None = None,
        agent_id: str | None = None,
    ) -> EvasionVerdict:
        if session_id is not None or agent_id is not None:
            attempt = replace(
                attempt,
                session_id=session_id if session_id is not None else attempt.session_id,
                agent_id=agent_id if agent_id is not None else attempt.agent_id,
            )
        verdict = self._detector.observe(attempt)
        if verdict.detected:
            self._store.append_event(evasion_event(verdict, attempt, occurred_at=self._clock()))
        return verdict
