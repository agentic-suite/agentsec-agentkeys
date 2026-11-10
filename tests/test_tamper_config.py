"""9.4 — config integrity: a pinned config that changes fails closed with a loud event."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.store.memory import MemoryStore
from agentkeys.tamper import ConfigIntegrity, TamperError, TamperGuard, config_digest


def _write(path: Path, text: str = 'enforce_mode = "enforce"\n') -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_a_pinned_unchanged_config_verifies(tmp_path: Path) -> None:
    path = _write(tmp_path / "config.toml")
    integrity = ConfigIntegrity(path)
    digest = integrity.pin()
    assert digest == config_digest(path)
    verdict = integrity.verify()
    assert verdict.ok is True
    assert verdict.reason is None


def test_an_edited_config_fails_closed_and_emits_tamper(tmp_path: Path) -> None:
    path = _write(tmp_path / "config.toml")
    integrity = ConfigIntegrity(path)
    integrity.pin()
    _write(path, 'enforce_mode = "monitor"\n')

    store = MemoryStore()
    store.open()
    guard = TamperGuard(store, integrity, clock=lambda: 1234)
    with pytest.raises(TamperError, match="config-tampered"):
        guard.check(session_id="s1")
    rows = store.read_ledger()
    assert len(rows) == 1
    event = rows[0].event
    assert event.event_name == "tamper-detected"
    assert event.severity == "high"
    assert event.session_id == "s1"
    assert "config-tampered" in (event.reason or "")
    assert event.occurred_at == 1234


def test_verify_before_pin_is_not_ok(tmp_path: Path) -> None:
    integrity = ConfigIntegrity(_write(tmp_path / "config.toml"))
    verdict = integrity.verify()
    assert verdict.ok is False
    assert verdict.reason == "config-not-pinned"


def test_a_missing_config_is_a_tamper_class_failure(tmp_path: Path) -> None:
    integrity = ConfigIntegrity(tmp_path / "missing.toml")
    with pytest.raises(TamperError, match="config-missing"):
        integrity.pin()


def test_a_config_removed_after_pin_fails_closed(tmp_path: Path) -> None:
    path = _write(tmp_path / "config.toml")
    integrity = ConfigIntegrity(path)
    integrity.pin()
    path.unlink()
    verdict = integrity.verify()
    assert verdict.ok is False
    assert "config-missing" in (verdict.reason or "")


def test_an_intact_guard_does_not_write_an_event(tmp_path: Path) -> None:
    path = _write(tmp_path / "config.toml")
    integrity = ConfigIntegrity(path)
    integrity.pin()
    store = MemoryStore()
    store.open()
    verdict = TamperGuard(store, integrity).check()
    assert verdict.ok is True
    assert store.read_ledger() == ()
