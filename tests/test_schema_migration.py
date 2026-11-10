"""12.3 — forward migrations on open, and a loud downgrade refusal (E11)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agentkeys.store.contract import StoreVersionError
from agentkeys.store.schema import CURRENT_SCHEMA_VERSION, migrate
from agentkeys.store.sqlite import SqliteStore


def test_an_empty_store_migrates_forward(tmp_path: Path) -> None:
    path = tmp_path / "new.db"
    store = SqliteStore(path)
    store.open()
    try:
        assert store.schema_version() == CURRENT_SCHEMA_VERSION
    finally:
        store.close()
    connection = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        connection.close()
    assert {"ledger", "issuances", "sessions", "revocations"} <= tables


def test_a_newer_schema_refuses_to_open(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    store = SqliteStore(path)
    store.open()
    store.close()
    connection = sqlite3.connect(path)
    connection.execute("UPDATE schema_version SET version = 999")
    connection.commit()
    connection.close()

    with pytest.raises(StoreVersionError, match="newer than supported"):
        SqliteStore(path).open()


def test_migrate_refuses_a_downgrade_without_writing(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "x.db")
    try:
        connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
        connection.execute("INSERT INTO schema_version (version) VALUES (999)")
        connection.commit()
        with pytest.raises(StoreVersionError):
            migrate(connection)
    finally:
        connection.close()
