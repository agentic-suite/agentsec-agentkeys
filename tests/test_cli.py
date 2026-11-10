"""0.2 — CLI surface: `--help` lists every command; stubs refuse honestly; `version` works."""

from __future__ import annotations

import pytest

from agentkeys.cli import COMMANDS, main

# The frozen v0.1.0 surface (WBS 0.2; docs/reference/cli.md).
EXPECTED_COMMANDS = (
    "init",
    "doctor",
    "scan",
    "migrate",
    "ref",
    "run",
    "revoke",
    "replay",
    "context-dump",
    "scan-usable",
    "export",
    "verify-log",
    "conformance",
    "serve",
    "version",
)


def test_command_surface_is_frozen() -> None:
    assert tuple(COMMANDS) == EXPECTED_COMMANDS


def test_top_level_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--help"])
    assert excinfo.value.code == 0
    out = capsys.readouterr().out
    for command in EXPECTED_COMMANDS:
        assert command in out


@pytest.mark.parametrize(
    "command",
    [
        c
        for c in EXPECTED_COMMANDS
        if c
        not in {
            "version",
            "doctor",
            "ref",
            "run",
            "revoke",
            "replay",
            "export",
            "verify-log",
            "scan",
            "migrate",
        }
    ],
)
def test_broker_commands_refuse_honestly(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    code = main([command])
    err = capsys.readouterr().err
    assert code != 0
    assert command in err
    assert "not implemented" in err.lower()


@pytest.mark.parametrize("command", EXPECTED_COMMANDS)
def test_subcommand_help_exits_zero(command: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main([command, "--help"])
    assert excinfo.value.code == 0
    assert command in capsys.readouterr().out


def test_version_prints_version(capsys: pytest.CaptureFixture[str]) -> None:
    import agentkeys

    assert main(["version"]) == 0
    assert agentkeys.__version__ in capsys.readouterr().out


def test_unknown_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["definitely-not-a-command"])
    err = capsys.readouterr().err
    assert code == 1
    assert err.strip()


def test_no_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([])
    assert code == 1
    assert "usage" in capsys.readouterr().err.lower()


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "agentkeys" in capsys.readouterr().out


def test_stub_json_mode_emits_stable_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    import json

    code = main(["context-dump", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == 1
    assert payload["ok"] is False
    assert payload["exit_class"] == "usage"
    assert "reason" in payload
    assert payload["receipts"] == []


def test_documented_flags_are_accepted(capsys: pytest.CaptureFixture[str]) -> None:
    # Stubs must expose the flags from docs/reference/cli.md in --help, and parse them.
    for argv in (
        ["run", "--server", "x"],
        ["revoke", "--agent", "a1"],
        ["replay", "--last"],
        ["context-dump", "--session", "s1"],
        ["export", "--session", "s1"],
        ["migrate", "file.env", "NAME"],
        ["ref", "list"],
        ["ref", "show", "ref_1"],
        ["conformance", "--suite", "all"],
    ):
        with pytest.raises(SystemExit) as excinfo:
            main([*argv, "--help"])
        assert excinfo.value.code == 0
        capsys.readouterr()
