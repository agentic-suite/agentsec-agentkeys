"""9.3 — enforce mode blocks where composed and names the gap where it is not (SC-17)."""

from __future__ import annotations

from agentkeys.evasion import AccessAttempt, EvasionDetector, EvasionMonitor
from agentkeys.store.memory import MemoryStore


def test_enforce_mode_blocks_when_an_enforcer_composes() -> None:
    calls: list[str] = []

    def enforcer(attempt: AccessAttempt) -> bool:
        calls.append(attempt.path)
        return True

    verdict = EvasionDetector(mode="enforce", enforcer=enforcer).observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assert verdict.blocked is True
    assert verdict.gap_named is False
    assert calls == ["/repo/.env"]


def test_enforce_mode_names_the_gap_when_the_enforcer_declines() -> None:
    verdict = EvasionDetector(mode="enforce", enforcer=lambda attempt: False).observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assert verdict.blocked is False
    assert verdict.gap_named is True
    assert "gap" in (verdict.reason or "")


def test_enforce_mode_without_an_enforcer_never_fakes_a_block() -> None:
    verdict = EvasionDetector(mode="enforce").observe(
        AccessAttempt(path="/home/u/.aws/credentials", principal="agent-1")
    )
    assert verdict.detected is True
    assert verdict.blocked is False
    assert verdict.gap_named is True
    assert "no enforcer" in (verdict.reason or "")


def test_a_failing_enforcer_is_a_named_gap_not_a_block() -> None:
    def broken(attempt: AccessAttempt) -> bool:
        raise RuntimeError("enforcer unavailable")

    verdict = EvasionDetector(mode="enforce", enforcer=broken).observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assert verdict.blocked is False
    assert verdict.gap_named is True


def test_monitor_mode_never_consults_the_enforcer() -> None:
    def enforcer(attempt: AccessAttempt) -> bool:
        raise AssertionError("monitor must not enforce")

    verdict = EvasionDetector(mode="monitor", enforcer=enforcer).observe(
        AccessAttempt(path="/repo/.env", principal="agent-1")
    )
    assert verdict.blocked is False


def test_enforce_mode_is_still_logged() -> None:
    store = MemoryStore()
    store.open()
    monitor = EvasionMonitor(store, EvasionDetector(mode="enforce", enforcer=lambda attempt: True))
    monitor.record(AccessAttempt(path="/repo/.env", principal="agent-1"), session_id="s1")
    event = store.read_ledger()[0].event
    assert event.event_name == "evasion-detected"
    assert "blocked" in (event.reason or "")
