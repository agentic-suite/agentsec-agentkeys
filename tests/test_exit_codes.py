"""0.3 — the reserved exit-code contract is frozen and complete."""

from __future__ import annotations

import pytest

from agentkeys.cli import main
from agentkeys.exit_codes import EXIT_CLASS, ExitCode, json_envelope

FROZEN = {
    "OK": 0,
    "USAGE": 1,
    "DENIED": 2,
    "TAMPER": 3,
    "REVOKE_VERIFIED": 4,
}


def test_codes_are_frozen() -> None:
    assert {member.name: int(member) for member in ExitCode} == FROZEN


def test_every_code_has_a_stable_machine_name() -> None:
    assert set(EXIT_CLASS) == set(ExitCode)
    assert len(set(EXIT_CLASS.values())) == len(EXIT_CLASS)
    assert EXIT_CLASS[ExitCode.DENIED] == "denied"


@pytest.mark.parametrize(("code", "ok"), [(ExitCode.OK, True), (ExitCode.USAGE, False)])
def test_envelope_shape(code: ExitCode, ok: bool) -> None:
    envelope = json_envelope(code)
    assert envelope["ok"] is ok
    assert envelope["exit_class"] == EXIT_CLASS[code]
    assert envelope["receipts"] == []
    assert "reason" not in envelope


def test_envelope_carries_reason_when_denied() -> None:
    envelope = json_envelope(ExitCode.DENIED, reason="backend locked", data={"backend": "file"})
    assert envelope == {
        "ok": False,
        "exit_class": "denied",
        "reason": "backend locked",
        "data": {"backend": "file"},
        "receipts": [],
    }


def test_commands_return_reserved_codes() -> None:
    assert main(["version"]) == ExitCode.OK
    assert main(["context-dump"]) == ExitCode.USAGE
