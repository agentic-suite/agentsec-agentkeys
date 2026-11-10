"""8.5 — `scan`/`migrate` CLI: stable JSON, masked output, and an honest `--ci` not-yet."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from agentkeys.cli import main

FIXTURES = Path(__file__).parent / "fixtures" / "scan_repo"
PLANTED = "ghp_FAKE0000000000000000000000000000000000"
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
    return home


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    target = tmp_path / "repo"
    shutil.copytree(FIXTURES, target)
    return target


def test_scan_json_is_stable_and_masked(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scan", "--root", str(repo), "--json"]) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["data"]["findings"]
    assert PLANTED not in out


def test_scan_human_output_is_masked(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scan", "--root", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "GITHUB_TOKEN" in out
    assert "broad-reuse" in out
    assert PLANTED not in out


def test_scan_ci_mode_refuses_honestly(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["scan", "--root", str(repo), "--ci"]) == 1
    err = capsys.readouterr().err
    assert "not yet" in err.lower()


def test_migrate_cli_moves_the_value(
    home: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["migrate", str(repo / ".env"), "GITHUB_TOKEN", "--root", str(repo)]) == 0
    assert PLANTED not in (repo / ".env").read_text(encoding="utf-8")
    assert PLANTED not in capsys.readouterr().out
    credentials = home / "credentials.json"
    assert credentials.exists()
    assert credentials.stat().st_mode & 0o777 == 0o600
    assert PLANTED in credentials.read_text(encoding="utf-8")  # the backend holds the value


def test_migrate_dry_run_is_masked_and_writes_nothing(
    home: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = (repo / ".env").read_bytes()
    assert main(["migrate", str(repo / ".env"), "GITHUB_TOKEN", "--root", str(repo), "--dry-run"]) == 0
    assert (repo / ".env").read_bytes() == before
    assert not (home / "credentials.json").exists()
    assert PLANTED not in capsys.readouterr().out


def test_migrate_unknown_name_is_denied(
    home: Path, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["migrate", str(repo / ".env"), "NOPE", "--root", str(repo)]) == 2
    assert "NOPE" in capsys.readouterr().err
