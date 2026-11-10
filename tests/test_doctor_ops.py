"""12.4 — doctor hardening: chain, serve lock, config integrity (E4/E10)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.events import build_event
from agentkeys.ops import lock_path
from agentkeys.store.sqlite import SqliteStore
from agentkeys.tamper import config_digest

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
        store.append_event(
            build_event("issuance.created", occurred_at=1000, session_id="s1", reference_id="ref_1")
        )
    finally:
        store.close()
    return home


def test_a_healthy_store_reports_chain_and_lock_checks(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    checks = {check["id"]: check for check in payload["data"]["checks"]}
    assert checks["chain"]["status"] == "ok"
    assert checks["serve-lock"]["status"] == "ok"
    assert checks["config-integrity"]["status"] == "ok"


def test_a_broken_chain_is_tamper(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 1")
    connection.commit()
    connection.close()
    assert main(["doctor", "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    checks = {check["id"]: check for check in payload["data"]["checks"]}
    assert checks["chain"]["status"] == "fail"
    assert "seq 1" in checks["chain"]["detail"]


def test_a_stale_lock_is_a_denial(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    lock_path(home).write_text(json.dumps({"pid": 999_999_999}), encoding="utf-8")
    assert main(["doctor", "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    checks = {check["id"]: check for check in payload["data"]["checks"]}
    assert checks["serve-lock"]["status"] == "fail"


def test_a_pinned_config_mismatch_is_tamper(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config_path = home / "config.toml"
    pinned = config_path.with_suffix(config_path.suffix + ".sha256")
    pinned.write_text("0" * 64, encoding="utf-8")
    assert config_digest(config_path) != "0" * 64
    assert main(["doctor", "--json"]) == 3
    payload = json.loads(capsys.readouterr().out)
    checks = {check["id"]: check for check in payload["data"]["checks"]}
    assert checks["config-integrity"]["status"] == "fail"


def test_an_unpinned_config_is_ok(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["doctor", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    checks = {check["id"]: check for check in payload["data"]["checks"]}
    assert checks["config-integrity"]["detail"] == "not pinned"
