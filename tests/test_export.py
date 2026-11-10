"""7.3/7.4 — deterministic secret-free export, and `verify-log` detects tamper (SC-29/SC-30/SC-31)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentkeys.cli import main
from agentkeys.events import build_event
from agentkeys.export import export_reference, export_session, render_rows
from agentkeys.ledger import verify_chain
from agentkeys.store.memory import MemoryStore
from agentkeys.store.sqlite import SqliteStore


def _seed(store: MemoryStore | SqliteStore) -> None:
    store.append_event(
        build_event(
            "issuance.created",
            occurred_at=1000,
            session_id="s1",
            reference_id="ref_1",
            issuance_id="iss_1",
        )
    )
    store.append_event(
        build_event(
            "use", occurred_at=1001, session_id="s1", reference_id="ref_1", issuance_id="iss_1"
        )
    )
    store.append_event(
        build_event(
            "exchange-rejected",
            occurred_at=1002,
            session_id="s1",
            issuance_id="iss_1",
            reason="audience-mismatch",
        )
    )
    store.append_event(
        build_event(
            "issuance.created",
            occurred_at=1003,
            session_id="s2",
            reference_id="ref_2",
            issuance_id="iss_2",
        )
    )


def test_session_export_is_ordered_jsonl_and_deterministic() -> None:
    store = MemoryStore()
    store.open()
    _seed(store)
    first = export_session(store, "s1")
    second = export_session(store, "s1")
    assert first.text == second.text
    lines = [json.loads(line) for line in first.text.splitlines()]
    assert [line["seq"] for line in lines] == [1, 2, 3]
    assert [line["event"]["event_name"] for line in lines] == [
        "issuance.created",
        "use",
        "exchange-rejected",
    ]
    assert all({"seq", "event", "prev_hash", "hash"} <= set(line) for line in lines)


def test_reference_export_selects_by_reference() -> None:
    store = MemoryStore()
    store.open()
    _seed(store)
    result = export_reference(store, "ref_2")
    lines = [json.loads(line) for line in result.text.splitlines()]
    assert len(lines) == 1
    assert lines[0]["event"]["session_id"] == "s2"


def test_export_is_secret_free() -> None:
    from agentkeys.redact import looks_like_secret

    store = MemoryStore()
    store.open()
    _seed(store)
    result = export_session(store, "s1")
    assert not looks_like_secret(result.text)
    assert "sk-" not in result.text


def test_export_to_a_file_is_0600(tmp_path: Path) -> None:
    store = MemoryStore()
    store.open()
    _seed(store)
    out = tmp_path / "session.jsonl"
    result = export_session(store, "s1", out=out)
    assert result.path == out
    assert out.exists()
    assert out.stat().st_mode & 0o777 == 0o600
    assert out.read_text(encoding="utf-8").rstrip("\n") == result.text


def test_render_rows_matches_the_chain() -> None:
    store = MemoryStore()
    store.open()
    _seed(store)
    rows = store.read_ledger()
    lines = [json.loads(line) for line in render_rows(rows).splitlines()]
    assert [line["hash"] for line in lines] == [row.hash for row in rows]
    assert verify_chain(rows).intact is True


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
        _seed(store)
    finally:
        store.close()
    return home


def test_verify_log_reports_an_intact_chain(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["verify-log", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["data"]["rows"] == 4
    assert payload["data"]["intact"] is True


def test_verify_log_detects_a_tampered_row(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import sqlite3

    connection = sqlite3.connect(home / "agentkeys.db")
    connection.execute("UPDATE ledger SET reason = 'rewritten' WHERE seq = 2")
    connection.commit()
    connection.close()

    assert main(["verify-log"]) == 3
    assert "2" in capsys.readouterr().err


def test_export_cli_writes_a_session_timeline(
    home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "out.jsonl"
    assert main(["export", "--session", "s1", "--out", str(out)]) == 0
    assert len(out.read_text(encoding="utf-8").splitlines()) == 3
    assert out.stat().st_mode & 0o777 == 0o600
    assert "s1" in capsys.readouterr().out


def test_export_cli_requires_exactly_one_selector(
    home: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["export"]) == 1
    assert capsys.readouterr().err.strip()
