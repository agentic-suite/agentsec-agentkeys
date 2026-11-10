"""1.6 — driver selection: entry points, admission, and refusal of unconformant drivers."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.store import contract as c
from agentkeys.store.loader import admit_driver, available_drivers, load_driver
from agentkeys.store.memory import MemoryStore
from agentkeys.store.sqlite import SqliteStore


class MissingConsume:
    """A driver that is otherwise plausible but has no `consume`."""

    def capabilities(self) -> c.CapabilityFlags:
        return c.CapabilityFlags(True, True, True, False)

    def open(self) -> None: ...

    def close(self) -> None: ...

    def create_reference(self, reference: c.Reference) -> c.Reference:
        return reference


def test_built_in_drivers_are_registered() -> None:
    assert {"memory", "sqlite"} <= set(available_drivers())


def test_load_sqlite_and_memory(tmp_path: Path) -> None:
    sqlite_store = load_driver("sqlite", path=tmp_path / "db.sqlite")
    assert isinstance(sqlite_store, SqliteStore)
    assert isinstance(load_driver("memory"), MemoryStore)


def test_unknown_driver_is_a_usage_error_naming_the_known_ones() -> None:
    with pytest.raises(c.DriverNotFound, match="sqlite"):
        load_driver("nope")


def test_unconformant_driver_is_refused_with_the_missing_method() -> None:
    with pytest.raises(c.DriverError, match="consume"):
        admit_driver("missing-consume", MissingConsume)


def test_conformant_driver_is_admitted() -> None:
    store = admit_driver("memory-ish", MemoryStore)
    assert callable(store.open)


def test_a_factory_target_is_supported(tmp_path: Path) -> None:
    store = admit_driver("factory", lambda: SqliteStore(tmp_path / "f.db"))
    assert isinstance(store, SqliteStore)


def test_an_unimportable_entry_point_value_is_refused() -> None:
    with pytest.raises(c.DriverError, match="import"):
        admit_driver("bad", "agentkeys.nope:Missing")


def test_required_capabilities_are_enforced_only_when_asked() -> None:
    assert load_driver("memory", required=("durable",)).capabilities().durable is False
    with pytest.raises(c.CapabilityError, match="durable"):
        load_driver("memory", required=("durable",), enforce=True)
