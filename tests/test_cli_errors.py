"""Error-path coverage for the M6-M10 CLI surfaces (usage, denied, tamper)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.events import build_event
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
reference = "ref_1"
audience = "api.github.com"
tool = "gh"
"""


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
        store.append_event(
            build_event(
                "issuance.created",
                occurred_at=1000,
                session_id="s1",
                agent_id="a1",
                reference_id="ref_1",
                issuance_id="iss_1",
            )
        )
    finally:
        store.close()
    return home


def test_revoke_flags_are_mutually_exclusive(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["revoke", "--agent", "a1", "--session", "s1"]) == 1
    assert capsys.readouterr().err.strip()


def test_revoke_json_unknown_target(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "--session", "ghost", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_class"] == "denied"
    assert "ghost" in payload["reason"]


def test_revoke_positional_all(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "all"]) == 0
    assert "s1" in capsys.readouterr().out


def test_revoke_with_a_bad_config_is_denied(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["revoke", "--session", "s1", "--config", "/nope/config.toml"]) == 2
    assert "config" in capsys.readouterr().err.lower()


def test_replay_with_a_bad_config_is_denied(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["replay", "--last", "--config", "/nope/config.toml"]) == 2
    assert capsys.readouterr().err.strip()


def test_scan_missing_root_is_denied(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["scan", "--root", str(tmp_path / "missing")]) == 2
    assert "not a directory" in capsys.readouterr().err


def test_scan_ci_json_is_an_honest_usage_error(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scan", "--root", str(home), "--ci", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_class"] == "usage"
    assert "not yet" in payload["reason"].lower()


def test_verify_log_json_tamper_names_the_seq(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import sqlite3

    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("UPDATE ledger SET reason = 'changed' WHERE seq = 1")
    connection.commit()
    connection.close()
    assert main(["verify-log", "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_class"] == "tamper"
    assert payload["data"]["first_bad_seq"] == 1


def test_verify_log_with_a_bad_config_is_denied(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["verify-log", "--config", "/nope/config.toml", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_class"] == "denied"


def test_export_reference_json(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["export", "--reference", "ref_1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["selector"] == "reference"
    assert payload["data"]["rows"] == 1


def test_export_with_a_bad_config_is_denied(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["export", "--session", "s1", "--config", "/nope/config.toml"]) == 2


def test_export_prints_jsonl_without_out(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["export", "--session", "s1"]) == 0
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines and json.loads(lines[0])["seq"] == 1


def test_migrate_requires_a_file_and_name(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["migrate"]) == 1
    assert "FILE NAME" in capsys.readouterr().err


def test_migrate_refuses_an_unsupported_backend(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["migrate", str(tmp_path / ".env"), "X", "--backend", "keychain"]) == 1
    assert "not yet available" in capsys.readouterr().err


def test_migrate_with_a_bad_config_is_denied(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".env").write_text("X=ghp_FAKE0000000000000000000000000000000000\n")
    assert (
        main(
            [
                "migrate",
                str(tmp_path / ".env"),
                "X",
                "--root",
                str(tmp_path),
                "--config",
                "/nope/config.toml",
            ]
        )
        == 2
    )
