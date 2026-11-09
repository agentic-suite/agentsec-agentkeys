"""The SQLite reference driver: WAL, fsync'd commits, one writer (M1, PRD 15 §5)."""

from __future__ import annotations

import os
import sqlite3
import uuid
from dataclasses import replace
from pathlib import Path

from agentkeys.store import schema
from agentkeys.store.contract import (
    GENESIS_PREV_HASH,
    Binding,
    CapabilityFlags,
    ConsumeResult,
    Issuance,
    LedgerEvent,
    LedgerRow,
    RedactionReceipt,
    Reference,
    Revocation,
    RevokeResult,
    Session,
    StoreBusyError,
    StoreError,
    StoreVersionError,
    compute_hash,
    require_capabilities,
)

__all__ = ["SqliteStore"]

_DIR_MODE = 0o700
_FILE_MODE = 0o600
_CRASH_POINT_ENV = "AGENTKEYS_TEST_CRASH_POINT"


def _is_memory(path: Path) -> bool:
    return str(path) in {":memory:", ""}


class SqliteStore:
    """Single-file SQLite store: one writer, durable commits, hash-chained ledger."""

    def __init__(self, path: str | Path, *, busy_timeout_ms: int = 5000) -> None:
        self.path = Path(path) if str(path) not in {":memory:", ""} else Path(":memory:")
        self._memory = _is_memory(Path(str(path)))
        self._busy_timeout_ms = busy_timeout_ms
        self._connection: sqlite3.Connection | None = None
        self._crash_point = os.environ.get(_CRASH_POINT_ENV, "")

    # ------------------------------------------------------------------ lifecycle

    def capabilities(self) -> CapabilityFlags:
        return CapabilityFlags(
            single_writer=True,
            durable=not self._memory,
            atomic_issue=True,
            cluster_safe=False,
        )

    def open(self) -> None:
        if not self._memory:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            try:
                self.path.parent.chmod(_DIR_MODE)
            except OSError:  # pragma: no cover - permission change is best-effort on odd filesystems
                pass
        connection = sqlite3.connect(
            ":memory:" if self._memory else str(self.path),
            isolation_level=None,
            timeout=self._busy_timeout_ms / 1000,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute(f"PRAGMA busy_timeout={self._busy_timeout_ms}")
        self._connection = connection
        try:
            schema.migrate(connection)
        except StoreVersionError:
            connection.close()
            self._connection = None
            raise
        if not self._memory:
            try:
                self.path.chmod(_FILE_MODE)
            except OSError:  # pragma: no cover
                pass

    def close(self) -> None:
        if self._connection is not None:
            self._connection.close()
            self._connection = None

    def pragma(self, name: str) -> str:
        return str(self._connection.execute(f"PRAGMA {name}").fetchone()[0])  # type: ignore[union-attr]

    def schema_version(self) -> int | None:
        """The store's schema version, or `None` when the store is not open."""
        if self._connection is None:
            return None
        return schema.read_version(self._connection)

    def begin_immediate(self) -> None:
        self._execute("BEGIN IMMEDIATE")

    def commit(self) -> None:
        self._connection.execute("COMMIT")  # type: ignore[union-attr]

    def rollback(self) -> None:
        self._connection.execute("ROLLBACK")  # type: ignore[union-attr]

    @property
    def _db(self) -> sqlite3.Connection:
        if self._connection is None:  # pragma: no cover - guarded by open() in every entry point
            raise StoreError("store is not open")
        return self._connection

    def _execute(self, sql: str, params: tuple[object, ...] = ()) -> sqlite3.Cursor:
        try:
            return self._db.execute(sql, params)
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc) or "busy" in str(exc):
                raise StoreBusyError(f"store is busy: {self.path}") from exc
            raise StoreError(str(exc)) from exc
        except sqlite3.IntegrityError as exc:
            raise StoreError(str(exc)) from exc

    # ------------------------------------------------------------------ references

    def create_reference(self, reference: Reference) -> Reference:
        self.begin_immediate()
        try:
            row = self._execute(
                '''SELECT * FROM "references" WHERE reference_id = ?''', (reference.reference_id,)
            ).fetchone()
            if row is not None:
                existing = _reference(row)
                if existing != reference:
                    raise StoreError(f"reference conflict: {reference.reference_id}")
                self.commit()
                return existing
            self._execute(
                '''INSERT INTO "references" (reference_id, akref_version, backend, path, class,'''
                " scope_hint, label, created_at, created_by) VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    reference.reference_id,
                    reference.akref_version,
                    reference.backend,
                    reference.path,
                    reference.class_,
                    reference.scope_hint,
                    reference.label,
                    reference.created_at,
                    reference.created_by,
                ),
            )
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return reference

    def get_reference(self, reference_id: str) -> Reference | None:
        row = self._execute(
            '''SELECT * FROM "references" WHERE reference_id = ?''', (reference_id,)
        ).fetchone()
        return None if row is None else _reference(row)

    def list_references(self) -> tuple[Reference, ...]:
        rows = self._execute('''SELECT * FROM "references" ORDER BY reference_id''').fetchall()
        return tuple(_reference(row) for row in rows)

    # ------------------------------------------------------------------ sessions

    def create_session(self, session: Session) -> Session:
        self.begin_immediate()
        try:
            row = self._execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session.session_id,)
            ).fetchone()
            if row is not None:
                self.commit()
                return _session(row)
            self._execute(
                "INSERT INTO sessions (session_id, agent_id, harness, started_at, ended_at,"
                " status, revoke_epoch, principal) VALUES (?,?,?,?,?,?,?,?)",
                (
                    session.session_id,
                    session.agent_id,
                    session.harness,
                    session.started_at,
                    session.ended_at,
                    session.status,
                    session.revoke_epoch,
                    session.principal,
                ),
            )
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return session

    def get_session(self, session_id: str) -> Session | None:
        row = self._execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
        return None if row is None else _session(row)

    def get_binding(self, binding_hash: str) -> Binding | None:
        row = self._execute(
            "SELECT * FROM bindings WHERE binding_hash = ?", (binding_hash,)
        ).fetchone()
        return None if row is None else _binding(row)

    # ------------------------------------------------------------------ issuance

    def issue(
        self,
        *,
        reference_id: str,
        session_id: str,
        agent_id: str,
        audience: str,
        tool: str,
        class_: str,
        ttl_seconds: int,
        window: int,
        secret_hash: str,
        single_use: bool,
        issued_at: int,
        provenance_json: str,
        binding_hash: str,
        event: LedgerEvent,
    ) -> Issuance:
        self.begin_immediate()
        try:
            existing = self._execute(
                "SELECT * FROM issuances WHERE binding_hash = ? AND window = ?",
                (binding_hash, window),
            ).fetchone()
            if existing is not None:
                self.commit()
                return _issuance(existing)

            issuance_id = f"iss_{uuid.uuid4().hex}"
            issuance = Issuance(
                issuance_id=issuance_id,
                binding_hash=binding_hash,
                window=window,
                reference_id=reference_id,
                session_id=session_id,
                agent_id=agent_id,
                audience=audience,
                tool=tool,
                class_=class_,
                ttl_seconds=ttl_seconds,
                issued_at=issued_at,
                expires_at=issued_at + ttl_seconds,
                secret_hash=secret_hash,
                single_use=single_use,
                consumed_at=None,
                provenance_json=provenance_json,
                status="live",
            )
            self._execute(
                "INSERT INTO bindings (binding_hash, reference_id, audience, tool, session_id,"
                " first_seen_at, issuance_count) VALUES (?,?,?,?,?,?,1)"
                " ON CONFLICT(binding_hash) DO UPDATE SET issuance_count = issuance_count + 1",
                (binding_hash, reference_id, audience, tool, session_id, issued_at),
            )
            self._execute(
                "INSERT INTO issuances (issuance_id, binding_hash, window, reference_id,"
                " session_id, agent_id, audience, tool, class, ttl_seconds, issued_at,"
                " expires_at, secret_hash, single_use, consumed_at, provenance_json, status)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,?,?)",
                (
                    issuance_id,
                    binding_hash,
                    window,
                    reference_id,
                    session_id,
                    agent_id,
                    audience,
                    tool,
                    class_,
                    ttl_seconds,
                    issued_at,
                    issuance.expires_at,
                    secret_hash,
                    int(single_use),
                    provenance_json,
                    "live",
                ),
            )
            self._append_event_locked(replace(event, issuance_id=issuance_id))
            if self._crash_point == "after_write_before_commit":  # test-only hook (S5)
                os._exit(70)
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return issuance

    def get_issuance(self, issuance_id: str) -> Issuance | None:
        row = self._execute(
            "SELECT * FROM issuances WHERE issuance_id = ?", (issuance_id,)
        ).fetchone()
        return None if row is None else _issuance(row)

    def find_issuance(self, binding_hash: str, window: int) -> Issuance | None:
        row = self._execute(
            "SELECT * FROM issuances WHERE binding_hash = ? AND window = ?",
            (binding_hash, window),
        ).fetchone()
        return None if row is None else _issuance(row)

    def consume(self, issuance_id: str, *, now: int) -> ConsumeResult:
        self.begin_immediate()
        try:
            row = self._execute(
                "SELECT * FROM issuances WHERE issuance_id = ?", (issuance_id,)
            ).fetchone()
            if row is None:
                self.commit()
                return ConsumeResult(status="unknown", issuance=None)
            issuance = _issuance(row)
            if issuance.consumed_at is not None:
                self.commit()
                return ConsumeResult(status="already_consumed", issuance=issuance)
            if issuance.expires_at <= now:
                self.commit()
                return ConsumeResult(status="expired", issuance=issuance)
            self._execute(
                "UPDATE issuances SET consumed_at = ?, status = 'consumed'"
                " WHERE issuance_id = ? AND consumed_at IS NULL",
                (now, issuance_id),
            )
            updated = self._execute(
                "SELECT * FROM issuances WHERE issuance_id = ?", (issuance_id,)
            ).fetchone()
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return ConsumeResult(status="consumed", issuance=_issuance(updated))

    def list_live(self, now: int) -> tuple[Issuance, ...]:
        rows = self._execute(
            "SELECT * FROM issuances WHERE status = 'live' AND consumed_at IS NULL"
            " AND expires_at > ? ORDER BY issued_at, issuance_id",
            (now,),
        ).fetchall()
        return tuple(_issuance(row) for row in rows)

    # ------------------------------------------------------------------ revocation

    def cas_revoke(
        self,
        *,
        scope: str,
        target_id: str,
        requested_by: str,
        requested_at: int,
        reason: str,
        event: LedgerEvent,
    ) -> RevokeResult:
        self.begin_immediate()
        try:
            row = self._execute(
                "SELECT * FROM sessions WHERE session_id = ?", (target_id,)
            ).fetchone()
            if row is None:
                raise StoreError(f"unknown target: {target_id}")
            session = _session(row)
            if session.revoke_epoch > 0:
                winner_row = self._execute(
                    "SELECT * FROM revocations WHERE scope = ? AND target_id = ?"
                    " ORDER BY requested_at DESC, revocation_id DESC LIMIT 1",
                    (scope, target_id),
                ).fetchone()
                self.commit()
                if winner_row is None:  # pragma: no cover - epoch implies a revocation row
                    raise StoreError(f"revocation epoch set without a record: {target_id}")
                return RevokeResult(
                    revocation=_revocation(winner_row),
                    winner=False,
                    epoch_before=session.revoke_epoch,
                    epoch_after=session.revoke_epoch,
                )
            cursor = self._execute(
                "UPDATE sessions SET revoke_epoch = revoke_epoch + 1"
                " WHERE session_id = ? AND revoke_epoch = ?",
                (target_id, session.revoke_epoch),
            )
            if cursor.rowcount != 1:  # pragma: no cover - single writer; CAS loss is a race
                raise StoreBusyError("revocation lost a concurrent race")
            revocation = Revocation(
                revocation_id=f"rev_{uuid.uuid4().hex}",
                scope=scope,
                target_id=target_id,
                requested_by=requested_by,
                requested_at=requested_at,
                effective_at=requested_at,
                reason=reason,
                epoch_after=session.revoke_epoch + 1,
            )
            self._execute(
                "INSERT INTO revocations (revocation_id, scope, target_id, requested_by,"
                " requested_at, effective_at, reason, epoch_after) VALUES (?,?,?,?,?,?,?,?)",
                (
                    revocation.revocation_id,
                    scope,
                    target_id,
                    requested_by,
                    requested_at,
                    requested_at,
                    reason,
                    revocation.epoch_after,
                ),
            )
            self._append_event_locked(event)
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return RevokeResult(
            revocation=revocation,
            winner=True,
            epoch_before=session.revoke_epoch,
            epoch_after=session.revoke_epoch + 1,
        )

    def get_revocation(self, revocation_id: str) -> Revocation | None:
        row = self._execute(
            "SELECT * FROM revocations WHERE revocation_id = ?", (revocation_id,)
        ).fetchone()
        return None if row is None else _revocation(row)

    # ------------------------------------------------------------------ ledger

    def append_event(self, event: LedgerEvent) -> LedgerRow:
        self.begin_immediate()
        try:
            row = self._append_event_locked(event)
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return row

    def _append_event_locked(self, event: LedgerEvent) -> LedgerRow:
        last = self._execute("SELECT seq, hash FROM ledger ORDER BY seq DESC LIMIT 1").fetchone()
        seq = 1 if last is None else int(last["seq"]) + 1
        prev_hash = GENESIS_PREV_HASH if last is None else str(last["hash"])
        digest = compute_hash(event, prev_hash)
        try:
            self._execute(
                "INSERT INTO ledger (seq, event_id, event_version, event_name, occurred_at,"
                " monotonic_ms, session_id, agent_id, reference_id, issuance_id, binding_json,"
                " ttl_seconds, principal, reason, severity, prev_hash, hash)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    seq,
                    event.event_id,
                    event.event_version,
                    event.event_name,
                    event.occurred_at,
                    event.monotonic_ms,
                    event.session_id,
                    event.agent_id,
                    event.reference_id,
                    event.issuance_id,
                    event.binding_json,
                    event.ttl_seconds,
                    event.principal,
                    event.reason,
                    event.severity,
                    prev_hash,
                    digest,
                ),
            )
        except StoreError as exc:
            if "UNIQUE" in str(exc):
                raise StoreError(f"duplicate event_id: {event.event_id}") from exc
            raise
        return LedgerRow(seq=seq, event=event, prev_hash=prev_hash, hash=digest)

    def read_ledger(self, since_seq: int = 0) -> tuple[LedgerRow, ...]:
        rows = self._execute(
            "SELECT * FROM ledger WHERE seq > ? ORDER BY seq", (since_seq,)
        ).fetchall()
        return tuple(_ledger_row(row) for row in rows)

    def export_session(self, session_id: str) -> tuple[LedgerRow, ...]:
        rows = self._execute(
            "SELECT * FROM ledger WHERE session_id = ? ORDER BY seq", (session_id,)
        ).fetchall()
        return tuple(_ledger_row(row) for row in rows)

    # ------------------------------------------------------------------ receipts

    def add_receipt(self, receipt: RedactionReceipt) -> RedactionReceipt:
        self.begin_immediate()
        try:
            self._execute(
                "INSERT INTO redaction_receipts (receipt_id, subject_id, field, class, count,"
                " redactor_version, created_at) VALUES (?,?,?,?,?,?,?)",
                (
                    receipt.receipt_id,
                    receipt.subject_id,
                    receipt.field,
                    receipt.class_,
                    receipt.count,
                    receipt.redactor_version,
                    receipt.created_at,
                ),
            )
        except BaseException:
            self.rollback()
            raise
        self.commit()
        return receipt

    def list_receipts(self, subject_id: str) -> tuple[RedactionReceipt, ...]:
        rows = self._execute(
            "SELECT * FROM redaction_receipts WHERE subject_id = ? ORDER BY created_at, receipt_id",
            (subject_id,),
        ).fetchall()
        return tuple(_receipt(row) for row in rows)


def _reference(row: sqlite3.Row) -> Reference:
    return Reference(
        reference_id=row["reference_id"],
        akref_version=row["akref_version"],
        backend=row["backend"],
        path=row["path"],
        class_=row["class"],
        scope_hint=row["scope_hint"],
        label=row["label"],
        created_at=row["created_at"],
        created_by=row["created_by"],
    )


def _session(row: sqlite3.Row) -> Session:
    return Session(
        session_id=row["session_id"],
        agent_id=row["agent_id"],
        harness=row["harness"],
        started_at=row["started_at"],
        ended_at=row["ended_at"],
        status=row["status"],
        revoke_epoch=row["revoke_epoch"],
        principal=row["principal"],
    )


def _binding(row: sqlite3.Row) -> Binding:
    return Binding(
        binding_hash=row["binding_hash"],
        reference_id=row["reference_id"],
        audience=row["audience"],
        tool=row["tool"],
        session_id=row["session_id"],
        first_seen_at=row["first_seen_at"],
        issuance_count=row["issuance_count"],
    )


def _issuance(row: sqlite3.Row) -> Issuance:
    return Issuance(
        issuance_id=row["issuance_id"],
        binding_hash=row["binding_hash"],
        window=row["window"],
        reference_id=row["reference_id"],
        session_id=row["session_id"],
        agent_id=row["agent_id"],
        audience=row["audience"],
        tool=row["tool"],
        class_=row["class"],
        ttl_seconds=row["ttl_seconds"],
        issued_at=row["issued_at"],
        expires_at=row["expires_at"],
        secret_hash=row["secret_hash"],
        single_use=bool(row["single_use"]),
        consumed_at=row["consumed_at"],
        provenance_json=row["provenance_json"],
        status=row["status"],
    )


def _revocation(row: sqlite3.Row) -> Revocation:
    return Revocation(
        revocation_id=row["revocation_id"],
        scope=row["scope"],
        target_id=row["target_id"],
        requested_by=row["requested_by"],
        requested_at=row["requested_at"],
        effective_at=row["effective_at"],
        reason=row["reason"],
        epoch_after=row["epoch_after"],
    )


def _ledger_event(row: sqlite3.Row) -> LedgerEvent:
    return LedgerEvent(
        event_id=row["event_id"],
        event_version=row["event_version"],
        event_name=row["event_name"],
        occurred_at=row["occurred_at"],
        monotonic_ms=row["monotonic_ms"],
        session_id=row["session_id"],
        agent_id=row["agent_id"],
        reference_id=row["reference_id"],
        issuance_id=row["issuance_id"],
        binding_json=row["binding_json"],
        ttl_seconds=row["ttl_seconds"],
        principal=row["principal"],
        reason=row["reason"],
        severity=row["severity"],
    )


def _ledger_row(row: sqlite3.Row) -> LedgerRow:
    return LedgerRow(
        seq=row["seq"],
        event=_ledger_event(row),
        prev_hash=row["prev_hash"],
        hash=row["hash"],
    )


def _receipt(row: sqlite3.Row) -> RedactionReceipt:
    return RedactionReceipt(
        receipt_id=row["receipt_id"],
        subject_id=row["subject_id"],
        field=row["field"],
        class_=row["class"],
        count=row["count"],
        redactor_version=row["redactor_version"],
        created_at=row["created_at"],
    )