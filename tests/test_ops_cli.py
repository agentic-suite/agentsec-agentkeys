"""12.1/12.2 — the `serve`, `backup`, and `restore` CLI surfaces."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.ops import lock_path
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
    store.close()
    return home


def test_backup_then_restore(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "backup.db"
    assert main(["backup", "--out", str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert out.exists()

    assert main(["restore", "--from", str(out), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["data"]["rows"] == 0


def test_backup_requires_out(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["backup"]) == 1
    assert "--out" in capsys.readouterr().err


def test_restore_requires_from(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["restore"]) == 1
    assert "--from" in capsys.readouterr().err


def test_backup_with_a_bad_config_is_denied(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["backup", "--out", str(tmp_path / "b.db"), "--config", "/nope"]) == 2
    assert capsys.readouterr().err.strip()


def test_serve_writes_user_units(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["serve", "--write-units", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    units = payload["data"]["units"]
    assert len(units) == 2
    for unit in units:
        assert Path(unit).is_file()
    assert not lock_path(home).exists()


def test_serve_with_a_bad_config_is_denied(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["serve", "--config", "/nope/config.toml"]) == 2
    assert "config" in capsys.readouterr().err.lower()


def test_serve_write_units_human_output(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["serve", "--write-units"]) == 0
    out = capsys.readouterr().out
    assert "agentkeys.launchd.plist" in out
    assert "agentkeys.service" in out


def test_serve_refuses_a_live_lock(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point the lock at a live PID (this test process) without starting a real server.
    import json as json_module
    import os

    lock_path(home).write_text(json_module.dumps({"pid": os.getpid()}), encoding="utf-8")

    from agentkeys.cli import _build_parser
    from agentkeys.commands.serve import run_serve

    args = _build_parser().parse_args(["serve"])
    assert run_serve(args) == 2
