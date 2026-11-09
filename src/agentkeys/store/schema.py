"""SQLite schema: DDL, version table, forward-only migrations (M1, PRD 15 §5-§6)."""

from __future__ import annotations

import sqlite3

from agentkeys.store.contract import StoreVersionError

__all__ = ["CURRENT_SCHEMA_VERSION", "MIGRATIONS", "migrate", "read_version"]

#: The schema version this binary writes and understands (M0's `doctor` reads the same table).
CURRENT_SCHEMA_VERSION = 1

_DDL_V1 = """
CREATE TABLE "references" (
  reference_id TEXT PRIMARY KEY, akref_version TEXT NOT NULL, backend TEXT NOT NULL,
  path TEXT NOT NULL, class TEXT NOT NULL, scope_hint TEXT, label TEXT,
  created_at INTEGER NOT NULL, created_by TEXT NOT NULL);
CREATE INDEX references_backend_path ON "references" (backend, path);

CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, harness TEXT NOT NULL,
  started_at INTEGER NOT NULL, ended_at INTEGER, status TEXT NOT NULL,
  revoke_epoch INTEGER NOT NULL DEFAULT 0, principal TEXT NOT NULL);
CREATE INDEX sessions_agent ON sessions (agent_id, status);

CREATE TABLE bindings (
  binding_hash TEXT PRIMARY KEY, reference_id TEXT NOT NULL, audience TEXT NOT NULL,
  tool TEXT NOT NULL, session_id TEXT NOT NULL, first_seen_at INTEGER NOT NULL,
  issuance_count INTEGER NOT NULL DEFAULT 0);
CREATE INDEX bindings_ref_session ON bindings (reference_id, session_id);

CREATE TABLE issuances (
  issuance_id TEXT PRIMARY KEY, binding_hash TEXT NOT NULL, window INTEGER NOT NULL,
  reference_id TEXT NOT NULL, session_id TEXT NOT NULL, agent_id TEXT NOT NULL,
  audience TEXT NOT NULL, tool TEXT NOT NULL, class TEXT NOT NULL,
  ttl_seconds INTEGER NOT NULL, issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
  secret_hash TEXT NOT NULL, single_use INTEGER NOT NULL, consumed_at INTEGER,
  provenance_json TEXT NOT NULL, status TEXT NOT NULL,
  UNIQUE (binding_hash, window));
CREATE INDEX issuances_session ON issuances (session_id, status);
CREATE INDEX issuances_expiry ON issuances (expires_at);

CREATE TABLE revocations (
  revocation_id TEXT PRIMARY KEY, scope TEXT NOT NULL, target_id TEXT NOT NULL,
  requested_by TEXT NOT NULL, requested_at INTEGER NOT NULL, effective_at INTEGER NOT NULL,
  reason TEXT NOT NULL, epoch_after INTEGER NOT NULL);
CREATE INDEX revocations_target ON revocations (scope, target_id);

CREATE TABLE backends (
  backend_id TEXT PRIMARY KEY, kind TEXT NOT NULL, display_name TEXT NOT NULL,
  capability_flags TEXT NOT NULL, health TEXT NOT NULL, conformance_version TEXT NOT NULL,
  added_at INTEGER NOT NULL);

CREATE TABLE redaction_receipts (
  receipt_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, field TEXT NOT NULL,
  class TEXT NOT NULL, count INTEGER NOT NULL, redactor_version TEXT NOT NULL,
  created_at INTEGER NOT NULL);
CREATE INDEX receipts_subject ON redaction_receipts (subject_id);

CREATE TABLE ledger (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
  event_version TEXT NOT NULL, event_name TEXT NOT NULL, occurred_at INTEGER NOT NULL,
  monotonic_ms INTEGER NOT NULL, session_id TEXT, agent_id TEXT, reference_id TEXT,
  issuance_id TEXT, binding_json TEXT, ttl_seconds INTEGER, principal TEXT,
  reason TEXT, severity TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE INDEX ledger_session_seq ON ledger (session_id, seq);
"""

#: Forward-only migrations: version N is produced by applying `MIGRATIONS[N]`.
MIGRATIONS: dict[int, str] = {1: _DDL_V1}


def read_version(connection: sqlite3.Connection) -> int:
    """Read the schema version; a store with other tables but no version table is corrupt."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    if "schema_version" not in tables:
        if tables - {"sqlite_sequence"}:
            raise StoreVersionError(
                "store has no schema_version table but is not empty; refusing (corrupt store)"
            )
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (0)")
        return 0
    row = connection.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
    if row is None:
        connection.execute("INSERT INTO schema_version (version) VALUES (0)")
        return 0
    return int(row[0])


def migrate(connection: sqlite3.Connection) -> int:
    """Apply forward migrations to `CURRENT_SCHEMA_VERSION`; refuse a newer store loudly."""
    version = read_version(connection)
    if version > CURRENT_SCHEMA_VERSION:
        raise StoreVersionError(
            f"store schema version {version} is newer than supported {CURRENT_SCHEMA_VERSION}; "
            "downgrade is refused"
        )
    while version < CURRENT_SCHEMA_VERSION:
        version += 1
        statements = [s.strip() for s in MIGRATIONS[version].split(";") if s.strip()]
        connection.execute("BEGIN IMMEDIATE")
        try:
            for statement in statements:
                connection.execute(statement)
            connection.execute("UPDATE schema_version SET version = ?", (version,))
            connection.execute("COMMIT")
        except sqlite3.Error:
            connection.execute("ROLLBACK")
            raise
    return version
