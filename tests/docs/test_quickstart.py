"""13.3 — the quickstart's exact commands, replayed end-to-end (CUJ-1)."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from agentkeys.cli import main

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
id = "file"
precedence = 1

[[bindings]]
reference = "akref:file/agentkeys/dev/github_token"
audience = "api.example.com"
tool = "call"
"""

ENV_FILE = "GITHUB_TOKEN=ghp_FAKE0000000000000000000000000000000000\n"
SECRET = "ghp_FAKE0000000000000000000000000000000000"
REFERENCE = "akref:file/agentkeys/dev/github_token"


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "ak"
    home.mkdir(mode=0o700)
    (home / "config.toml").write_text(CONFIG.replace("{home}", str(home)), encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".env").write_text(ENV_FILE, encoding="utf-8")
    return tmp_path


def test_the_quickstart_reaches_a_brokered_call_and_a_verified_kill(
    workspace: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = workspace / "repo"
    home = workspace / "ak"

    # scan: masked findings only
    assert main(["scan", "--root", str(repo), "--json"]) == 0
    scan_output = capsys.readouterr().out
    assert "GITHUB_TOKEN" in scan_output
    assert SECRET not in scan_output

    # migrate: value to the backend, site rewritten
    assert main(["migrate", str(repo / ".env"), "GITHUB_TOKEN", "--root", str(repo)]) == 0
    capsys.readouterr()
    assert SECRET not in (repo / ".env").read_text(encoding="utf-8")
    assert (home / "credentials.json").stat().st_mode & 0o777 == 0o600

    # ref list: references only
    assert main(["ref", "list", "--json"]) == 0
    refs = json.loads(capsys.readouterr().out)
    assert refs["data"]["references"][0]["backend"] == "file"

    # brokered child call: the child sees a scoped token at its own egress
    child = "import os,sys; sys.exit(0 if os.environ.get('AGENTKEYS_SCOPED_TOKEN') else 3)"
    monkeypatch.setenv("AGENTKEYS_SCOPED_TOKEN", REFERENCE)
    from agentkeys.cli import _build_parser
    from agentkeys.commands.run import run_run

    run_args = _build_parser().parse_args(
        ["run", "--server", REFERENCE, "--", sys.executable, "-c", child]
    )
    assert run_run(run_args, stdin=io.BytesIO(b""), stdout=io.BytesIO()) == 0
    capsys.readouterr()

    # revoke, then prove the replay fails (exit 4)
    assert main(["revoke", "--session", "stdio"]) == 0
    capsys.readouterr()
    assert main(["replay", "--last"]) == 4

    # evidence: deterministic secret-free export + intact chain
    out = workspace / "lifecycle.jsonl"
    assert main(["export", "--session", "stdio", "--out", str(out)]) == 0
    assert SECRET not in out.read_text(encoding="utf-8")
    assert main(["verify-log"]) == 0
