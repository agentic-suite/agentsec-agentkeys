"""13.1 — every CLI flag is documented, and the documented flags exist."""

from __future__ import annotations

import argparse
from pathlib import Path

from agentkeys.cli import _build_parser

DOC = Path(__file__).resolve().parents[2] / "docs" / "reference" / "cli.md"


def _flags(parser: argparse.ArgumentParser) -> set[str]:
    found: set[str] = set()
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for subparser in action.choices.values():
                found |= _flags(subparser)
        for option in action.option_strings:
            if option not in {"-h", "--help"}:
                found.add(option)
    return found


def test_every_cli_flag_is_documented() -> None:
    text = DOC.read_text(encoding="utf-8")
    missing = sorted(flag for flag in _flags(_build_parser()) if flag not in text)
    assert missing == [], f"undocumented flags: {missing}"


def test_every_documented_command_exists() -> None:
    from agentkeys.cli import COMMANDS

    text = DOC.read_text(encoding="utf-8")
    for command in COMMANDS:
        assert f"`agentkeys {command}" in text or f"`{command}`" in text, command
