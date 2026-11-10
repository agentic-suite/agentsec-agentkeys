"""6.3/6.1 — the `revoke` and `replay` CLI surfaces (exit codes and the replay proof)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.store.contract import Session
from agentkeys.store.sqlite import SqliteStore

CONFIG = """
enforce_mode = "enforce"
sink = ""

[store]
path = "{home}/agentkeys.db"

[clock]
skew_tolerance = 30

[ttl.dev]
floor = 30
ceiling = 900

[[backends]]
id = "keychain"
precedence = 1

[[bindings]]
reference = "akref:keychain/agentkeys/dev/token"
audience = "api.github.com"
tool = "gh"
"""

TTL = {"dev": TtlBound(floor=30, ceiling=900)}


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    (home / "config.toml").write_text(CONFIG.replace("{home}", str(home)), encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    store = SqliteStore(home / "agentkeys.db")
    store.open()
    try:
        store.create_session(
            Session(
                session_id="s1",
                agent_id="a1",
                harness="claude-code",
                started_at=1,
                ended_at=None,
                status="active",
                revoke_epoch=0,
                principal="op",
            )
        )
        ReferenceRegistry(store).register(
            ReferenceDoc(
                reference_id="ref_1",
                backend="keychain",
                path="agentkeys/dev/token",
                class_="dev",
                label="dev token",
            )
        )
    finally:
        store.close()
    return home


def _seed_issued(home: Path) -> str:
    """Resolve once so the ledger holds a pre-revoke `issuance.created` row."""
    store = SqliteStore(home / "agentkeys.db")
    store.open()
    try:
        core = ResolutionCore(
            store,
            ReferenceRegistry(store),
            ttl=TTL,
            bindings=(("ref_1", "api.github.com", "gh"),),
            clock=lambda: 1000,
        )
        return core.resolve(
            "ref_1", audience="api.github.com", tool="gh", session_id="s1"
        ).issuance.issuance_id
    finally:
        store.close()


def test_revoke_session_via_cli(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "--session", "s1", "--reason", "operator"]) == 0
    out = capsys.readouterr().out
    assert "s1" in out
    store = SqliteStore(home / "agentkeys.db")
    store.open()
    try:
        session = store.get_session("s1")
        assert session is not None
        assert session.revoke_epoch == 1
    finally:
        store.close()


def test_revoke_json_envelope(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "--agent", "a1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["exit_class"] == "ok"
    assert payload["data"]["scope"] == "agent"


def test_revoke_unknown_target_is_denied(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "--session", "ghost"]) == 2
    assert "ghost" in capsys.readouterr().err


def test_revoke_without_a_target_is_a_usage_error(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["revoke"]) == 1
    assert capsys.readouterr().err.strip()


def test_replay_verifies_a_refusal(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _seed_issued(home)
    assert main(["revoke", "--session", "s1"]) == 0
    capsys.readouterr()
    assert main(["replay", "--last", "--json"]) == 4
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["exit_class"] == "revoke_verified"
    assert "REFUSED" in payload["reason"]


def test_replay_before_a_revoke_does_not_claim_a_kill(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _seed_issued(home)
    assert main(["replay", "--last"]) == 2
    assert "no revoke" in capsys.readouterr().err.lower()


def test_replay_without_last_is_a_usage_error(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["replay"]) == 1
    assert capsys.readouterr().err.strip()
