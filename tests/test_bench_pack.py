"""14.8 — the published benchmark pack is present, well-formed, and matches the committed results."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "bench" / "results" / "killtime-contextdump.json"
RESULTS = ROOT / "field-test" / "v0.1.0" / "results"


def _pack() -> dict[str, object]:
    payload: dict[str, object] = json.loads(PACK.read_text(encoding="utf-8"))
    return payload


def test_the_pack_and_readme_are_published() -> None:
    assert PACK.is_file()
    assert (ROOT / "bench" / "README.md").is_file()


def test_the_pack_declares_its_format_and_machine() -> None:
    payload = _pack()
    assert payload["format"] == "agentkeys-bench/1.0"
    assert payload["release"] == "v0.1.0"
    assert payload["git_sha"]
    machine = payload["machine"]
    assert isinstance(machine, dict)
    assert {"platform", "system", "machine", "python", "docker"} <= set(machine)


def test_kill_time_matches_the_committed_result() -> None:
    payload = _pack()
    kill = payload["kill_time"]
    assert isinstance(kill, dict)
    assert kill["case"] == "FT-RK-KILLTIME"
    assert kill["status"] == "pass"
    assert kill["iterations"] >= 100
    assert kill["p95_ms"] <= 1000.0
    assert kill["max_ms"] <= 1000.0
    assert kill["replay_failures"] == kill["iterations"]

    committed = json.loads(
        (RESULTS / "FT-RK-KILLTIME" / "summary.json").read_text(encoding="utf-8")
    )
    assert committed["status"] == "pass"
    asserted = {item["name"]: item["actual"] for item in committed["assertions"]}
    assert kill["p95_ms"] == asserted["p95-lte-1s"]
    assert kill["max_ms"] == asserted["max-lte-1s"]


def test_zero_secret_claims_are_published_and_green() -> None:
    payload = _pack()
    for key, case in (
        ("context_dump", "FT-AP-CONTEXTDUMP"),
        ("evidence", "FT-AP-EVIDENCE"),
        ("scan_migrate", "FT-MP-SCANMIGRATE"),
    ):
        claim = payload[key]
        assert isinstance(claim, dict)
        assert claim["case"] == case
        assert claim["status"] == "pass"
        assert claim["assertions"]
        committed = json.loads((RESULTS / case / "summary.json").read_text(encoding="utf-8"))
        assert committed["status"] == "pass"
