"""13.4 — the eight runbooks exist and each ends in an executable verification."""

from __future__ import annotations

from pathlib import Path

RUNBOOKS = Path(__file__).resolve().parents[2] / "docs" / "runbooks"

EXPECTED = (
    "rb-1-locked-backend.md",
    "rb-2-store-corruption.md",
    "rb-3-suspected-exfiltration.md",
    "rb-4-config-drift.md",
    "rb-5-upgrade-day.md",
    "rb-6-sink-outage.md",
    "rb-7-revoke-drill.md",
    "rb-8-secret-rotation.md",
)


def test_all_eight_runbooks_exist() -> None:
    found = sorted(path.name for path in RUNBOOKS.glob("*.md"))
    assert found == sorted(EXPECTED)


def test_each_runbook_has_symptom_steps_and_verification() -> None:
    for name in EXPECTED:
        text = (RUNBOOKS / name).read_text(encoding="utf-8")
        assert "## Symptom" in text, name
        assert "## Steps" in text, name
        assert "## Verification" in text, name


def test_runbook_verifications_name_a_real_command() -> None:
    commands = ("agentkeys ", "python -m agentkeys")
    for name in EXPECTED:
        text = (RUNBOOKS / name).read_text(encoding="utf-8")
        verification = text.split("## Verification", 1)[1]
        assert any(command in verification for command in commands), name
