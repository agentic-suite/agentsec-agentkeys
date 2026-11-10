"""1.T — crash recovery and durable-commit-before-ack (S5/S6 of the store design)."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from agentkeys.store.sqlite import SqliteStore
from tests.store_fixtures import issue_kwargs

_CRASHING_ISSUE = textwrap.dedent(
    """
    import sys
    from agentkeys.store.sqlite import SqliteStore
    from agentkeys.store.contract import Reference, Session, LedgerEvent

    store = SqliteStore(sys.argv[1])
    store.open()
    store.create_reference(Reference(
        reference_id="ref_1", akref_version="1.0", backend="keychain", path="p",
        class_="dev", scope_hint=None, label=None, created_at=1, created_by="op"))
    store.create_session(Session(
        session_id="s1", agent_id="a1", harness="h", started_at=1, ended_at=None,
        status="active", revoke_epoch=0, principal="op"))
    store.issue(
        reference_id="ref_1", session_id="s1", agent_id="a1", audience="aud",
        tool="gh", class_="dev", ttl_seconds=60, window=1, secret_hash="hash_1",
        single_use=True, issued_at=1000, provenance_json="{}", binding_hash="bh_1",
        event=LedgerEvent(event_id="evt_1", event_version="1.0", event_name="issuance.created",
            occurred_at=1000, monotonic_ms=5, session_id="s1", agent_id="a1",
            reference_id="ref_1", issuance_id=None, binding_json="{}", ttl_seconds=60,
            principal="op", reason=None, severity="info"))
    print("should have crashed")
    """
)


def _run_crashing_issue(path: Path) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "AGENTKEYS_TEST_CRASH_POINT": "after_write_before_commit"}
    return subprocess.run(
        [sys.executable, "-c", _CRASHING_ISSUE, str(path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_a_crash_mid_issue_leaves_no_partial_state(tmp_path: Path) -> None:
    path = tmp_path / "crash.db"
    completed = _run_crashing_issue(path)
    assert completed.returncode == 70, completed.stderr
    assert "should have crashed" not in completed.stdout

    store = SqliteStore(path)
    store.open()
    try:
        assert store.read_ledger() == ()
        assert store.find_issuance("bh_1", 1) is None
        assert store.get_binding("bh_1") is None
        # the seed committed before the crash and survives
        assert store.get_reference("ref_1") is not None
        assert store.get_session("s1") is not None
    finally:
        store.close()


def test_a_retry_after_a_crash_issues_exactly_once(tmp_path: Path) -> None:
    path = tmp_path / "retry.db"
    assert _run_crashing_issue(path).returncode == 70

    store = SqliteStore(path)
    store.open()
    try:
        first = store.issue(**issue_kwargs())
        retry = store.issue(**issue_kwargs(event_id="evt_retry"))
        assert first == retry
        assert len(store.read_ledger()) == 1
        binding = store.get_binding("bh_1")
        assert binding is not None and binding.issuance_count == 1
    finally:
        store.close()


def test_the_crash_hook_is_inert_without_the_environment_variable(tmp_path: Path) -> None:
    path = tmp_path / "no-crash.db"
    env = {k: v for k, v in os.environ.items() if k != "AGENTKEYS_TEST_CRASH_POINT"}
    completed = subprocess.run(
        [sys.executable, "-c", _CRASHING_ISSUE, str(path)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert completed.returncode == 0
    assert "should have crashed" in completed.stdout
    store = SqliteStore(path)
    store.open()
    try:
        assert len(store.read_ledger()) == 1
    finally:
        store.close()


def test_a_committed_issue_is_visible_to_a_second_store(tmp_path: Path) -> None:
    path = tmp_path / "durable.db"
    first = SqliteStore(path)
    first.open()
    issuance_id = first.issue(**issue_kwargs()).issuance_id
    first.close()

    second = SqliteStore(path)
    second.open()
    try:
        assert second.capabilities().durable is True
        found = second.get_issuance(issuance_id)
        assert found is not None and found.status == "live"
        assert [row.seq for row in second.read_ledger()] == [1]
    finally:
        second.close()


def test_memory_driver_is_honest_about_durability() -> None:
    from agentkeys.store.memory import MemoryStore

    assert MemoryStore().capabilities().durable is False
