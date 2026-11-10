"""Operational surface: serve lock, WAL-safe backup/restore, retention markers, drills (M12).

Every operation is fail-closed: a live lock blocks restore, a broken chain blocks both backup and
restore, a newer schema refuses to load, and pruning never deletes a ledger row.
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from agentkeys.bench.killtime import KillTimeReport, run_benchmark
from agentkeys.core.resolution import ResolutionCore
from agentkeys.events import build_event
from agentkeys.ledger import ChainReport, verify_chain
from agentkeys.store.contract import BrokerStore, LedgerEvent, LedgerRow
from agentkeys.store.sqlite import SqliteStore
from agentkeys.tamper import TamperError

__all__ = [
    "BackupManifest",
    "BrokerService",
    "LockState",
    "RetentionPolicy",
    "backup_store",
    "inspect_lock",
    "restore_store",
    "run_drill",
]

_LOCK_NAME = "serve.lock"
_FILE_MODE = 0o600


def lock_path(home: str | Path) -> Path:
    """The serve lock location for a broker home."""
    return Path(home) / _LOCK_NAME


@dataclass(frozen=True)
class LockState:
    """Whether a serve lock is absent, live, or stale."""

    state: str
    pid: int | None = None
    detail: str = ""


def inspect_lock(home: str | Path) -> LockState:
    """Read the lock and test the PID; a dead PID is a stale lock (never silently ignored)."""
    path = lock_path(home)
    if not path.is_file():
        return LockState("absent", detail=f"no lock: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        pid = int(payload["pid"])
    except (OSError, ValueError, KeyError, json.JSONDecodeError):
        return LockState("stale", detail=f"unreadable lock: {path}")
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return LockState("stale", pid=pid, detail=f"stale lock (pid {pid} is gone)")
    except PermissionError:  # a live process owned by someone else still holds the lock
        return LockState("live", pid=pid, detail=f"lock held by pid {pid}")
    return LockState("live", pid=pid, detail=f"lock held by pid {pid}")


class BrokerService:
    """A foreground broker process: one writer, a lock file, clean SIGTERM shutdown."""

    def __init__(self, store_path: str | Path, home: str | Path) -> None:
        self.store = SqliteStore(store_path)
        self.home = Path(home)
        self._stop = threading.Event()

    def start(self) -> None:
        """Open the store and publish the lock; refuse a live lock."""
        state = inspect_lock(self.home)
        if state.state == "live":
            raise RuntimeError(f"broker already running: {state.detail}")
        if state.state == "stale":
            self._remove_lock()
        self.store.open()
        self.home.mkdir(parents=True, exist_ok=True)
        os.chmod(self.home, 0o700)
        path = lock_path(self.home)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(
                {
                    "pid": os.getpid(),
                    "started_at": int(time.time()),
                    "store": str(self.store.path),
                },
                handle,
                sort_keys=True,
            )
        os.chmod(path, _FILE_MODE)

    def stop(self) -> None:
        """Close the store and remove the lock (idempotent)."""
        self._stop.set()
        self.store.close()
        self._remove_lock()

    def wait(self) -> None:
        """Block until SIGTERM/SIGINT; then stop cleanly."""
        for signal_number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signal_number, lambda *_: self._stop.set())
        try:
            self._stop.wait()
        finally:
            self.stop()

    def _remove_lock(self) -> None:
        path = lock_path(self.home)
        if path.exists():
            path.unlink()


@dataclass(frozen=True)
class BackupManifest:
    """What a backup carries besides the database (references only, plus the chain head)."""

    path: Path
    schema_version: int
    rows: int
    chain_head: str
    created_at: int

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "schema_version": self.schema_version,
            "rows": self.rows,
            "chain_head": self.chain_head,
            "created_at": self.created_at,
            "contains_secrets": False,
            "contents": "references, bindings, issuance hashes, ledger, receipts",
        }


def _read_rows(path: str | Path) -> tuple[LedgerRow, ...]:
    """Read ledger rows read-only (no migration, no write) for verification."""
    connection = sqlite3.connect(f"file:{Path(path)}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute("SELECT * FROM ledger ORDER BY seq").fetchall()
    finally:
        connection.close()
    from agentkeys.store.sqlite import _ledger_row

    return tuple(_ledger_row(row) for row in rows)


def _verify(path: str | Path) -> ChainReport:
    return verify_chain(_read_rows(path))


def backup_store(
    store_path: str | Path, out: str | Path, *, created_at: int | None = None
) -> BackupManifest:
    """WAL-safe online copy, then verify the copy's chain; a broken chain aborts."""
    source = Path(store_path)
    target = Path(out)
    if not source.is_file():
        raise FileNotFoundError(f"store not found: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with (
        sqlite3.connect(str(source)) as source_connection,
        sqlite3.connect(str(target)) as target_connection,
    ):
        source_connection.backup(target_connection)
    os.chmod(target, _FILE_MODE)
    report = _verify(target)
    if not report.intact:
        raise TamperError(f"backup chain is broken at seq {report.first_bad_seq}")
    with sqlite3.connect(f"file:{target}?mode=ro", uri=True) as connection:
        version = int(connection.execute("SELECT version FROM schema_version").fetchone()[0])
    rows = _read_rows(target)
    manifest = BackupManifest(
        path=target,
        schema_version=version,
        rows=len(rows),
        chain_head=rows[-1].hash if rows else "0" * 64,
        created_at=int(time.time()) if created_at is None else created_at,
    )
    manifest_path = target.with_suffix(target.suffix + ".manifest.json")
    descriptor = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, _FILE_MODE)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(manifest.to_dict(), handle, sort_keys=True)
    os.chmod(manifest_path, _FILE_MODE)
    return manifest


def restore_store(
    backup_path: str | Path, store_path: str | Path, *, home: str | Path
) -> BackupManifest:
    """Restore a verified backup atomically; refuse a live broker or a broken chain."""
    state = inspect_lock(home)
    if state.state == "live":
        raise RuntimeError(f"refusing restore while the broker runs: {state.detail}")
    source = Path(backup_path)
    if not source.is_file():
        raise FileNotFoundError(f"backup not found: {source}")
    report = _verify(source)
    if not report.intact:
        raise TamperError(f"backup chain is broken at seq {report.first_bad_seq}")
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True) as connection:
        version = int(connection.execute("SELECT version FROM schema_version").fetchone()[0])
    from agentkeys.store.schema import CURRENT_SCHEMA_VERSION

    if version > CURRENT_SCHEMA_VERSION:
        raise RuntimeError(f"backup schema {version} is newer than supported")
    target = Path(store_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".restore")
    with (
        sqlite3.connect(str(source)) as source_connection,
        sqlite3.connect(str(temporary)) as target_connection,
    ):
        source_connection.backup(target_connection)
    os.chmod(temporary, _FILE_MODE)
    os.replace(temporary, target)
    rows = _read_rows(target)
    return BackupManifest(
        path=target,
        schema_version=version,
        rows=len(rows),
        chain_head=rows[-1].hash if rows else "0" * 64,
        created_at=int(time.time()),
    )


@dataclass(frozen=True)
class RetentionPolicy:
    """Append-only retention: a prune is a logged marker, never a delete."""

    store: BrokerStore

    def prune(self, before_seq: int, *, actor: str = "operator") -> LedgerEvent:
        if before_seq < 0:
            raise ValueError("before_seq must be >= 0")
        event = build_event(
            "retention-pruned",
            occurred_at=int(time.time()),
            principal=actor,
            reason=f"cutoff_seq={before_seq}; rows retained (append-only)",
        )
        self.store.append_event(event)
        return event


def run_drill(
    store: BrokerStore,
    core: ResolutionCore,
    *,
    reference_id: str,
    audience: str,
    tool: str,
    iterations: int = 100,
    clock: Callable[[], int] | None = None,
) -> tuple[KillTimeReport, int]:
    """Run the kill-time drill; returns the report and the generation instant."""
    report = run_benchmark(
        store,
        core,
        reference_id=reference_id,
        audience=audience,
        tool=tool,
        iterations=iterations,
    )
    return report, (clock or (lambda: int(time.time())))()
