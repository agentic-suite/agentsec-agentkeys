"""Session binding: one agent identity per session, dying with the session (M4, WBS 4.6; D-17)."""

from __future__ import annotations

from agentkeys.store.contract import BrokerStore, Session

__all__ = ["SessionBinder", "SessionConflict"]


class SessionConflict(Exception):
    """A second, different agent tried to claim a session, or the session is revoked."""


class SessionBinder:
    """Enforces the session's single agent identity through the BrokerStore contract."""

    def __init__(self, store: BrokerStore) -> None:
        self._store = store

    def bind(self, session_id: str, agent_id: str) -> Session:
        """Return the session for this agent; refuse a different agent or a revoked session."""
        session = self._store.get_session(session_id)
        if session is None:
            raise SessionConflict(f"unknown-session: {session_id}")
        if session.revoke_epoch > 0:
            raise SessionConflict(f"session-revoked: {session_id}")
        if session.agent_id != agent_id:
            raise SessionConflict(
                f"session {session_id} belongs to agent {session.agent_id}, not {agent_id}"
            )
        return session

    def agent_for(self, session_id: str) -> str | None:
        """The agent bound to a session, or `None` — never an ambient/inherited identity."""
        session = self._store.get_session(session_id)
        return None if session is None else session.agent_id
