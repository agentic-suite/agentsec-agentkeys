"""0.6 — `doctor`: read-only health checks, exit-coded, names every failure."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.doctor import CURRENT_SCHEMA_VERSION, check_platform, doctor_exit

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
reference = "agentkeys/dev/example-api-token"
audience = "api.github.com"
tool = "gh"
"""


def _home(tmp_path: Path, text: str = CONFIG, mode: int = 0o700) -> Path:
    home = tmp_path / "ak"
    home.mkdir(mode=mode, exist_ok=True)
    home.chmod(mode)
    if text is not None:
        (home / "config.toml").write_text(text.replace("{home}", str(home)), encoding="utf-8")
    return home


def test_healthy_fresh_install_is_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path)
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    monkeypatch.setenv("HOME", str(tmp_path))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["ok"] is True
    checks = {check["id"]: check["status"] for check in payload["data"]["checks"]}
    assert set(checks) >= {"platform", "config", "home", "store", "backends", "clock", "version"}
    assert set(checks.values()) == {"ok"}
    assert payload["data"]["effective_config"]["enforce_mode"] == "enforce"
    assert payload["data"]["effective_config"]["backends"] == ["keychain"]
    assert payload["data"]["effective_config"]["ttl"]["dev"] == {"floor": 30, "ceiling": 900}


def test_missing_config_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, text=None)  # type: ignore[arg-type]
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    assert payload["exit_class"] == "denied"
    checks = {check["id"]: check["status"] for check in payload["data"]["checks"]}
    assert checks["config"] == "fail"
    assert "not found" in payload["data"]["checks"][1]["detail"]


def test_literal_secret_in_config_is_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"
    home = _home(tmp_path, CONFIG.replace('sink = ""', f'sink = "{secret}"'))
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 3
    assert payload["exit_class"] == "tamper"
    assert secret not in json.dumps(payload)


def test_wrong_home_permissions_deny(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path, mode=0o755)
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    checks = {check["id"]: check["status"] for check in payload["data"]["checks"]}
    assert checks["home"] == "fail"


def test_absent_home_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("AGENTKEYS_HOME", str(tmp_path / "missing"))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    checks = {check["id"]: check["status"] for check in payload["data"]["checks"]}
    assert checks["home"] == "fail"


def test_corrupt_store_is_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path)
    (home / "agentkeys.db").write_text("this is not a database", encoding="utf-8")
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 3
    assert payload["exit_class"] == "tamper"


def test_known_store_version_is_healthy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path)
    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute("INSERT INTO schema_version (version) VALUES (?)", (CURRENT_SCHEMA_VERSION,))
    connection.commit()
    connection.close()
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    store = {check["id"]: check for check in payload["data"]["checks"]}["store"]
    assert store["status"] == "ok"
    assert str(CURRENT_SCHEMA_VERSION) in store["detail"]


def test_newer_store_version_is_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path)
    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("CREATE TABLE schema_version (version INTEGER NOT NULL)")
    connection.execute(
        "INSERT INTO schema_version (version) VALUES (?)", (CURRENT_SCHEMA_VERSION + 1,)
    )
    connection.commit()
    connection.close()
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    assert main(["doctor", "--json"]) == 3
    capsys.readouterr()


def test_missing_store_parent_denies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = CONFIG.replace("{home}/agentkeys.db", "{home}/nope/agentkeys.db")
    home = _home(tmp_path, text)
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    code = main(["doctor", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 2
    checks = {check["id"]: check["status"] for check in payload["data"]["checks"]}
    assert checks["store"] == "fail"
    assert "parent" in {check["id"]: check for check in payload["data"]["checks"]}["store"]["detail"]


def test_windows_platform_is_denied_with_a_clear_reason() -> None:
    result = check_platform("win32")
    assert result.status == "fail"
    assert "not supported" in result.detail.lower()


def test_supported_platforms_are_ok() -> None:
    assert check_platform("darwin").status == "ok"
    assert check_platform("linux").status == "ok"


def test_tamper_outranks_denied() -> None:
    from agentkeys.doctor import Check

    checks = [
        Check(id="a", status="fail", detail="denied"),
        Check(id="b", status="fail", detail="tamper", tamper=True),
    ]
    assert doctor_exit(checks) == 3
    assert doctor_exit([Check(id="a", status="fail", detail="denied")]) == 2
    assert doctor_exit([Check(id="a", status="ok", detail="")]) == 0


def test_human_output_names_each_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    home = _home(tmp_path)
    monkeypatch.setenv("AGENTKEYS_HOME", str(home))
    assert main(["doctor"]) == 0
    out = capsys.readouterr().out
    assert "config" in out
    assert "effective config" in out.lower()