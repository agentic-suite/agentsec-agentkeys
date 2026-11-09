"""1.5 — schema versioning: forward migration, loud downgrade refusal, corrupt store refusal."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from agentkeys.store import contract as c
from agentkeys.store import schema
from agentkeys.store.sqlite import SqliteStore
from tests.store_fixtures import make_reference

SCHEMA_TABLE = "CREATE TABLE schema_version (version INTEGER NOT NULL)"


def _raw(path: Path, statements: list[str]) -> None:
    connection = sqlite3.connect(path)
    try:
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def _version_of(path: Path) -> int:
    connection = sqlite3.connect(path)
    try:
        row = connection.execute("SELECT version FROM schema_version").fetchone()
    finally:
        connection.close()
    return int(row[0])


def test_a_fresh_store_is_at_the_current_version(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "fresh.db")
    store.open()
    try:
        assert store.schema_version() == schema.CURRENT_SCHEMA_VERSION
    finally:
        store.close()


def test_a_legacy_store_migrates_forward_and_is_usable(tmp_path: Path) -> None:
    path = tmp_path / "legacy.db"
    _raw(path, [SCHEMA_TABLE, "INSERT INTO schema_version (version) VALUES (0)"])
    store = SqliteStore(path)
    store.open()
    try:
        assert store.schema_version() == schema.CURRENT_SCHEMA_VERSION
        assert store.create_reference(make_reference()) == make_reference()
        connection = sqlite3.connect(path)
        try:
            tables = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
        finally:
            connection.close()
        assert {"references", "sessions", "bindings", "issuances", "ledger"} <= tables
    finally:
        store.close()


def test_a_newer_store_refuses_loudly_and_is_untouched(tmp_path: Path) -> None:
    path = tmp_path / "future.db"
    _raw(path, [SCHEMA_TABLE, "INSERT INTO schema_version (version) VALUES (2)"])
    store = SqliteStore(path)
    with pytest.raises(c.StoreVersionError, match="downgrade is refused"):
        store.open()
    assert _version_of(path) == 2
    assert store.schema_version() is None


def test_migration_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "twice.db"
    first = SqliteStore(path)
    first.open()
    first.close()
    second = SqliteStore(path)
    second.open()
    try:
        assert second.schema_version() == schema.CURRENT_SCHEMA_VERSION
    finally:
        second.close()


def test_a_corrupt_store_refuses_loudly(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.db"
    _raw(path, ["CREATE TABLE junk (x INTEGER)"])
    store = SqliteStore(path)
    with pytest.raises(c.StoreError, match="schema_version") as excinfo:
        store.open()
    assert not isinstance(excinfo.value, sqlite3.OperationalError)


def test_read_version_creates_the_table_when_absent() -> None:
    connection = sqlite3.connect(":memory:", isolation_level=None)
    try:
        assert schema.read_version(connection) == 0
        assert schema.read_version(connection) == 0
    finally:
        connection.close()


def test_migrations_cover_every_version_up_to_current() -> None:
    assert set(schema.MIGRATIONS) == set(range(1, schema.CURRENT_SCHEMA_VERSION + 1))
