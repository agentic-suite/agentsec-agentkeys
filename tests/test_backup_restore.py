"""12.2 — WAL-safe backup/restore with chain continuity and fail-closed refusals (E12)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agentkeys.events import build_event
from agentkeys.ledger import verify_chain
from agentkeys.ops import BrokerService, backup_store, restore_store
from agentkeys.store.sqlite import SqliteStore


def _seed(store_path: Path) -> None:
    store = SqliteStore(store_path)
    store.open()
    try:
        for index in range(3):
            store.append_event(
                build_event(
                    "issuance.created",
                    occurred_at=1000 + index,
                    session_id="s1",
                    reference_id="ref_1",
                    issuance_id=f"iss_{index}",
                )
            )
    finally:
        store.close()


def test_backup_is_wal_safe_and_carries_the_chain_head(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    out = tmp_path / "backup.db"
    manifest = backup_store(store_path, out, created_at=1234)

    assert out.exists()
    assert out.stat().st_mode & 0o777 == 0o600
    assert manifest.rows == 3
    assert manifest.created_at == 1234
    manifest_path = out.with_suffix(out.suffix + ".manifest.json")
    assert manifest_path.stat().st_mode & 0o777 == 0o600
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload["contains_secrets"] is False
    assert payload["chain_head"] == manifest.chain_head


def test_restore_preserves_the_chain(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    backup = tmp_path / "backup.db"
    backup_store(store_path, backup)

    target = tmp_path / "restored.db"
    manifest = restore_store(backup, target, home=tmp_path / "ak")
    store = SqliteStore(target)
    store.open()
    try:
        rows = store.read_ledger()
    finally:
        store.close()
    assert manifest.rows == 3
    assert verify_chain(rows).intact is True
    assert [row.event.issuance_id for row in rows] == ["iss_0", "iss_1", "iss_2"]


def test_a_tampered_backup_is_refused(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    backup = tmp_path / "backup.db"
    backup_store(store_path, backup)
    connection = sqlite3.connect(backup)
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 2")
    connection.commit()
    connection.close()

    with pytest.raises(Exception, match="broken at seq 2"):
        restore_store(backup, tmp_path / "restored.db", home=tmp_path / "ak")


def test_restore_refuses_while_the_broker_runs(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    backup = tmp_path / "backup.db"
    backup_store(store_path, backup)
    home = tmp_path / "ak"
    service = BrokerService(tmp_path / "running.db", home)
    service.start()
    try:
        with pytest.raises(RuntimeError, match="broker runs"):
            restore_store(backup, tmp_path / "restored.db", home=home)
    finally:
        service.stop()


def test_missing_inputs_are_loud(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        backup_store(tmp_path / "missing.db", tmp_path / "out.db")
    with pytest.raises(FileNotFoundError):
        restore_store(tmp_path / "missing.db", tmp_path / "out.db", home=tmp_path / "ak")


def test_a_newer_schema_backup_is_refused(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    backup = tmp_path / "backup.db"
    backup_store(store_path, backup)
    connection = sqlite3.connect(backup)
    connection.execute("UPDATE schema_version SET version = 99")
    connection.commit()
    connection.close()
    with pytest.raises(RuntimeError, match="newer than supported"):
        restore_store(backup, tmp_path / "restored.db", home=tmp_path / "ak")


def test_backup_refuses_a_broken_source_chain(tmp_path: Path) -> None:
    store_path = tmp_path / "agentkeys.db"
    _seed(store_path)
    connection = sqlite3.connect(store_path)
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 1")
    connection.commit()
    connection.close()
    with pytest.raises(Exception, match="chain is broken"):
        backup_store(store_path, tmp_path / "backup.db")
