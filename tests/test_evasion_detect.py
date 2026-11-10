"""9.1/9.2 — raw-credential reads outside the broker are high-severity, attributed events."""

from __future__ import annotations

import pytest

from agentkeys.evasion import (
    AccessAttempt,
    EvasionDetector,
    EvasionMonitor,
    classify_path,
)
from agentkeys.events import EVENT_NAMES
from agentkeys.store.memory import MemoryStore


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/repo/.env", "dotenv"),
        ("/repo/.env.production", "dotenv"),
        ("/home/u/.aws/credentials", "cloud-credential"),
        ("/home/u/.config/gcloud/application_default_credentials.json", "cloud-credential"),
        ("/Users/u/Library/Keychains/login.keychain-db", "keychain"),
        ("/home/u/.ssh/id_ed25519", "ssh-key"),
        ("/repo/keys/deploy.pem", "ssh-key"),
        ("/repo/README.md", None),
        ("/repo/src/app.py", None),
    ],
)
def test_paths_are_classified(path: str, expected: str | None) -> None:
    assert classify_path(path) == expected


def test_monitor_mode_detects_but_never_claims_a_block() -> None:
    verdict = EvasionDetector(mode="monitor").observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assert verdict.detected is True
    assert verdict.class_ == "dotenv"
    assert verdict.severity == "high"
    assert verdict.blocked is False
    assert verdict.gap_named is False


def test_an_unrelated_path_is_not_an_evasion() -> None:
    verdict = EvasionDetector(mode="monitor").observe(
        AccessAttempt(path="/repo/README.md", principal="agent-1")
    )
    assert verdict.detected is False
    assert verdict.class_ is None


def test_a_detected_attempt_is_one_high_severity_ledger_event() -> None:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="monitor"), clock=lambda: 1234)
    verdict = monitor.record(
        AccessAttempt(path="/home/u/.aws/credentials", principal="agent-1"), session_id="s1"
    )
    assert verdict.detected is True
    rows = store.read_ledger()
    assert len(rows) == 1
    event = rows[0].event
    assert event.event_name == "evasion-detected"
    assert event.event_name in EVENT_NAMES
    assert event.severity == "high"
    assert event.session_id == "s1"
    assert event.principal == "agent-1"
    assert "cloud-credential" in (event.reason or "")
    assert "/home/u/.aws/credentials" in (event.reason or "")
    assert event.occurred_at == 1234


def test_an_unrelated_read_records_nothing() -> None:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="monitor"))
    monitor.record(AccessAttempt(path="/repo/app.py", principal="agent-1"))
    assert store.read_ledger() == ()


def test_the_evasion_event_carries_no_secret_material() -> None:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="monitor"))
    monitor.record(AccessAttempt(path="/repo/.env", principal="agent-1"))
    event = store.read_ledger()[0].event
    assert "sk-" not in (event.reason or "")
