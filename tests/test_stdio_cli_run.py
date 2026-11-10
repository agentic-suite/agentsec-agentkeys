"""5.1 - `agentkeys run --server`: the CLI path that launches a server under the broker."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.commands.run import run_run
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.store.contract import Session
from agentkeys.store.sqlite import SqliteStore

KEY = "akref:keychain/agentkeys/dev/token"
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
audience = "stdio.local"
tool = "stdio"
"""


def _args(argv: list[str]) -> argparse.Namespace:
    from agentkeys.cli import _build_parser

    return _build_parser().parse_args(argv)


def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    (home / "config.toml").write_text(CONFIG.replace("{home}", str(home)), encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path))
    return home


def _seed(home: Path) -> None:
    store = SqliteStore(home / "agentkeys.db")
    store.open()
    try:
        store.create_session(
            Session(
                session_id="stdio",
                agent_id="stdio:stdio",
                harness="stdio",
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


def test_run_requires_a_server_reference(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["run", "--", "true"]) == 1
    assert "--server" in capsys.readouterr().err


def test_run_requires_a_child_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _home(tmp_path, monkeypatch)
    assert main(["run", "--server", KEY]) == 1
    assert "child command" in capsys.readouterr().err


def test_run_without_a_config_is_denied(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AGENTKEYS_HOME", str(tmp_path / "missing"))
    assert main(["run", "--server", KEY, "--", "true"]) == 2
    assert capsys.readouterr().err.strip()


def test_the_child_runs_with_a_substituted_token_and_no_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed(home)
    report = tmp_path / "child.json"
    monkeypatch.setenv("GITHUB_TOKEN", KEY)  # the documented placeholder pattern
    child = [
        sys.executable,
        "-c",
        (
            "import json, os\n"
            f"report = {str(report)!r}\n"
            "line = input()\n"
            "token = os.environ.get('GITHUB_TOKEN', '')\n"
            "open(report, 'w').write(json.dumps({\n"
            "  'token': token, 'has_reference': token.startswith('akref:'),\n"
            "  'received': json.loads(line)['method']}))\n"
            'print(\'{"jsonrpc":"2.0","id":1,"result":"ok"}\')\n'
        ),
    ]
    args = _args(["run", "--server", KEY, "--", *child])
    code = run_run(
        args,
        stdin=io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'),
        stdout=io.BytesIO(),
    )
    assert code == 0
    payload = json.loads(report.read_text())
    assert payload["has_reference"] is False
    assert payload["token"] and payload["token"] != KEY
    assert len(payload["token"]) == 32
    assert payload["received"] == "initialize"


def test_a_literal_client_secret_in_the_same_variable_is_stripped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = _home(tmp_path, monkeypatch)
    _seed(home)
    report = tmp_path / "child2.json"
    monkeypatch.setenv("GITHUB_TOKEN", "client-supplied-real-token")
    child = [
        sys.executable,
        "-c",
        (
            "import json, os\n"
            f"report = {str(report)!r}\n"
            "input()\n"
            "open(report, 'w').write(json.dumps({\n"
            "  'token': os.environ.get('GITHUB_TOKEN', '')}))\n"
        ),
    ]
    run_run(
        _args(["run", "--server", KEY, "--", *child]),
        stdin=io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'),
        stdout=io.BytesIO(),
    )
    assert json.loads(report.read_text())["token"] == ""
