"""2.6 - SDK and CLI control surface: resolve/use/revoke, and no secret read-out path."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.sdk import Broker
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

TTL = {"dev": TtlBound(floor=30, ceiling=900)}
BINDINGS = (("ref_1", "api.github.com", "gh"),)
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


def _session() -> Session:
    return Session(
        session_id="s1",
        agent_id="a1",
        harness="claude-code",
        started_at=1,
        ended_at=None,
        status="active",
        revoke_epoch=0,
        principal="op",
    )


def _reference() -> ReferenceDoc:
    return ReferenceDoc(
        reference_id="ref_1",
        backend="keychain",
        path="agentkeys/dev/token",
        class_="dev",
        label="dev token",
    )


@pytest.fixture
def store() -> MemoryStore:
    instance = MemoryStore()
    instance.open()
    instance.create_session(_session())
    return instance


@pytest.fixture
def broker(store: MemoryStore) -> Broker:
    registry = ReferenceRegistry(store)
    registry.register(_reference())
    core = ResolutionCore(store, registry, ttl=TTL, bindings=BINDINGS, clock=lambda: 1000)
    return Broker(core)


def test_the_sdk_exposes_no_secret_read_out(broker: Broker) -> None:
    public = [name for name in dir(broker) if not name.startswith("_")]
    assert "get_secret" not in public
    assert not any("secret" in name for name in public)
    assert not any("plaintext" in name for name in public)


def test_the_sdk_registers_lists_resolves_and_uses(broker: Broker) -> None:
    assert [doc.reference_id for doc in broker.list_references()] == ["ref_1"]
    resolved = broker.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert resolved.token is not None
    assert broker.use(resolved.issuance.issuance_id, resolved.token, now=1001).status == "consumed"
    assert broker.get_issuance(resolved.issuance.issuance_id) is not None


def test_the_sdk_revokes_a_session_unconditionally(broker: Broker) -> None:
    result = broker.revoke("s1", reason="operator", requested_by="op", requested_at=1100)
    assert result.winner is True
    with pytest.raises(ResolutionDenied, match="session-revoked"):
        broker.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")


def test_the_sdk_does_not_leak_the_token_in_repr(broker: Broker) -> None:
    resolved = broker.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1")
    assert resolved.token is not None
    assert resolved.token not in repr(resolved)


def _seed_store(path: Path) -> None:
    from agentkeys.store.sqlite import SqliteStore

    store = SqliteStore(path)
    store.open()
    try:
        store.create_session(_session())
        ReferenceRegistry(store).register(_reference())
    finally:
        store.close()


def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    (home / "config.toml").write_text(CONFIG.replace("{home}", str(home)), encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path))
    return home


def test_cli_ref_list_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed_store(home / "agentkeys.db")
    assert main(["ref", "list", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["references"][0]["reference_id"] == "ref_1"


def test_cli_ref_show_by_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed_store(home / "agentkeys.db")
    assert main(["ref", "show", "ref_1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["reference"]["backend"] == "keychain"


def test_cli_ref_show_unknown_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed_store(home / "agentkeys.db")
    code = main(["ref", "show", "ref_nope", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["exit_class"] == "denied"


def test_cli_ref_requires_a_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AGENTKEYS_HOME", str(tmp_path / "missing"))
    assert main(["ref", "list"]) == 2
    assert capsys.readouterr().err.strip()


def test_cli_ref_human_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed_store(home / "agentkeys.db")
    assert main(["ref", "list"]) == 0
    assert "akref:keychain/agentkeys/dev/token" in capsys.readouterr().out
    assert main(["ref", "show", "ref_1"]) == 0
    assert "keychain" in capsys.readouterr().out


def test_cli_ref_without_a_subcommand_is_usage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _home(tmp_path, monkeypatch)
    assert main(["ref"]) == 1
    assert "subcommand" in capsys.readouterr().err


def test_cli_ref_malformed_key_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed_store(home / "agentkeys.db")
    assert main(["ref", "show", "not-a-key"]) == 2
    assert capsys.readouterr().err.strip()


def test_cli_ref_with_a_broken_config_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    (home / "config.toml").write_text("enforce_mode = 5\n", encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    assert main(["ref", "list"]) == 2
    assert capsys.readouterr().err.strip()
