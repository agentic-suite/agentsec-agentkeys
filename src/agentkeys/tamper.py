"""Tamper resistance: config integrity and unknown-reference enumeration (M9, E10).

A tampered config fails closed with a loud `tamper-detected` event; it is never repaired into an
allow. Repeated unknown-reference probes raise the evasion-class enumeration signal.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agentkeys.events import build_event
from agentkeys.store.contract import BrokerStore

__all__ = [
    "ConfigIntegrity",
    "EnumerationSignal",
    "IntegrityVerdict",
    "TamperError",
    "TamperGuard",
    "config_digest",
]


class TamperError(Exception):
    """The broker detected tampering; issuance stops (fail closed, loud)."""


@dataclass(frozen=True)
class IntegrityVerdict:
    """The integrity check result: ok, or the reason it is not."""

    ok: bool
    reason: str | None = None
    digest: str | None = None


def config_digest(path: str | Path) -> str:
    """SHA-256 over the exact config bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ConfigIntegrity:
    """Pins the config digest at session start and refuses a later change."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._pinned: str | None = None

    def pin(self) -> str:
        """Record the current digest; a missing config is a tamper-class failure."""
        try:
            self._pinned = config_digest(self._path)
        except OSError as exc:
            raise TamperError(f"config-missing: {self._path}") from exc
        return self._pinned

    def verify(self) -> IntegrityVerdict:
        """Compare the current bytes with the pinned digest (never repairs)."""
        if self._pinned is None:
            return IntegrityVerdict(False, "config-not-pinned")
        try:
            current = config_digest(self._path)
        except OSError:
            return IntegrityVerdict(False, f"config-missing: {self._path}")
        if current != self._pinned:
            return IntegrityVerdict(
                False,
                f"config-tampered: {current[:12]} != {self._pinned[:12]}",
                current,
            )
        return IntegrityVerdict(True, None, current)


class TamperGuard:
    """Checks integrity, records `tamper-detected`, and denies on any non-ok verdict."""

    def __init__(
        self,
        store: BrokerStore,
        integrity: ConfigIntegrity,
        *,
        clock: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._integrity = integrity
        self._clock = clock or (lambda: int(time.time()))

    def check(
        self, *, session_id: str | None = None, agent_id: str | None = None
    ) -> IntegrityVerdict:
        verdict = self._integrity.verify()
        if verdict.ok:
            return verdict
        self._store.append_event(
            build_event(
                "tamper-detected",
                occurred_at=self._clock(),
                session_id=session_id,
                agent_id=agent_id,
                reason=verdict.reason,
                severity="high",
            )
        )
        raise TamperError(verdict.reason or "tamper detected")


class EnumerationSignal:
    """Counts unknown-reference probes in a sliding window and raises a signal at the threshold."""

    def __init__(
        self,
        *,
        threshold: int = 3,
        window_seconds: int = 60,
        clock: Callable[[], int] | None = None,
    ) -> None:
        if threshold < 1:
            raise ValueError("threshold must be >= 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be >= 1")
        self._threshold = threshold
        self._window = window_seconds
        self._clock = clock or (lambda: int(time.time()))
        self._probes: list[tuple[int, str | None]] = []

    def observe(self, reference_id: str, *, session_id: str | None = None) -> bool:
        """Record one unknown-reference probe; `True` once the threshold is crossed."""
        now = self._clock()
        self._probes = [
            (when, probe_session)
            for when, probe_session in self._probes
            if now - when <= self._window
        ]
        self._probes.append((now, session_id))
        return len(self._probes) >= self._threshold

    def reset(self) -> None:
        self._probes.clear()
