"""Revocation: one CAS per session, scoped fan-out, and the attributed `revoked` event (M6, R4).

Revocation is unconditional (D-07): the broker never asks policy for permission to kill. A scoped
revoke enumerates exactly the target's sessions and CASes each; `all` is explicit. An unknown
target is a loud error, never a silent no-op (SC-27).
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass

from agentkeys.store.contract import BrokerStore, LedgerEvent, RevokeResult, Session

__all__ = ["RevokeOutcome", "Revoker", "UnknownTarget"]

_SCOPES = ("session", "agent", "all")


class UnknownTarget(Exception):
    """A scoped revoke named a session/agent that does not exist (loud, never silent)."""


@dataclass(frozen=True)
class RevokeOutcome:
    """What one revoke command did: the CAS results and the events it recorded."""

    scope: str
    target: str | None
    requested_at: int
    revocations: tuple[RevokeResult, ...]
    events: tuple[LedgerEvent, ...]


class Revoker:
    """Revokes one session, one agent's sessions, or every session — recursively, never policy-gated."""

    def __init__(
        self,
        store: BrokerStore,
        *,
        clock: Callable[[], int] | None = None,
        monotonic_ms: Callable[[], int] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock or (lambda: int(time.time()))
        self._monotonic_ms = monotonic_ms or (lambda: time.monotonic_ns() // 1_000_000)

    def revoke(
        self,
        scope: str,
        target: str | None = None,
        *,
        reason: str,
        requested_by: str,
    ) -> RevokeOutcome:
        """Kill the target(s) for `scope`; unknown scoped targets raise `UnknownTarget`."""
        if scope not in _SCOPES:
            raise ValueError(f"unknown revoke scope: {scope!r} (expected one of {', '.join(_SCOPES)})")
        requested_at = self._clock()
        sessions = self._sessions_for(scope, target)
        results: list[RevokeResult] = []
        events: list[LedgerEvent] = []
        for session in sessions:
            event = self._event(session, reason=reason, requested_by=requested_by, now=requested_at)
            results.append(
                self._store.cas_revoke(
                    scope=scope,
                    target_id=session.session_id,
                    requested_by=requested_by,
                    requested_at=requested_at,
                    reason=reason,
                    event=event,
                )
            )
            events.append(event)
        return RevokeOutcome(
            scope=scope,
            target=target,
            requested_at=requested_at,
            revocations=tuple(results),
            events=tuple(events),
        )

    def _sessions_for(self, scope: str, target: str | None) -> tuple[Session, ...]:
        if scope == "all":
            if target is not None:
                raise ValueError("scope 'all' takes no target")
            sessions = self._store.list_sessions()
            if not sessions:
                raise UnknownTarget("all: no sessions to revoke")
            return sessions
        if target is None:
            raise ValueError(f"scope {scope!r} requires a target")
        if scope == "session":
            session = self._store.get_session(target)
            if session is None:
                raise UnknownTarget(f"unknown session: {target}")
            return (session,)
        sessions = tuple(
            session for session in self._store.list_sessions() if session.agent_id == target
        )
        if not sessions:
            raise UnknownTarget(f"unknown agent: {target}")
        return sessions

    def _event(
        self, session: Session, *, reason: str, requested_by: str, now: int
    ) -> LedgerEvent:
        return LedgerEvent(
            event_id=f"evt_{uuid.uuid4().hex}",
            event_version="1.0",
            event_name="revoked",
            occurred_at=now,
            monotonic_ms=self._monotonic_ms(),
            session_id=session.session_id,
            agent_id=session.agent_id,
            reference_id=None,
            issuance_id=None,
            binding_json=None,
            ttl_seconds=None,
            principal=requested_by,
            reason=reason,
            severity="high",
        )
