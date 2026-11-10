"""5.1/5.3 - a stock stdio server launches under the broker with references, not secrets."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from agentkeys.stdio.substitute import (
    SubstitutionError,
    build_virtualized_env,
    is_placeholder,
    receipts_to_store,
)
from agentkeys.stdio.wrapper import plan_launch, run_under_broker

REFERENCE = "akref:keychain/agentkeys/dev/token"
SCOPED = "scoped-stdio-token"


def _resolve(name: str, key: str) -> str:
    assert key == REFERENCE
    return SCOPED


def test_the_child_environment_holds_a_substituted_token_and_no_placeholder() -> None:
    substitution = build_virtualized_env(
        {"GITHUB_TOKEN": REFERENCE, "LOG_LEVEL": "info", "PATH": "/usr/bin"},
        resolve=_resolve,
    )
    assert substitution.env["GITHUB_TOKEN"] == SCOPED
    assert substitution.env["LOG_LEVEL"] == "info"
    assert substitution.replaced == ("GITHUB_TOKEN",)
    assert all(not is_placeholder(value) for value in substitution.env.values())


def test_a_placeholder_is_recognised_and_a_plain_value_is_not() -> None:
    assert is_placeholder(REFERENCE)
    assert not is_placeholder(SCOPED)


def test_a_malformed_placeholder_is_refused() -> None:
    with pytest.raises(SubstitutionError, match="malformed"):
        build_virtualized_env({"TOKEN": "akref:keychain/../escape"}, resolve=_resolve)


def test_a_placeholder_that_resolves_to_nothing_is_refused() -> None:
    with pytest.raises(SubstitutionError, match="nothing"):
        build_virtualized_env({"TOKEN": REFERENCE}, resolve=lambda name, key: "")


def test_receipts_are_emitted_for_every_substitution() -> None:
    substitution = build_virtualized_env({"TOKEN": REFERENCE}, resolve=_resolve)
    assert substitution.receipts
    assert substitution.receipts[0].field == "TOKEN"
    stored = receipts_to_store(substitution, subject_id="stdio", created_at=1000)
    assert stored[0].subject_id == "stdio"
    assert SCOPED not in stored[0].field


def test_the_launch_plan_marks_the_child_as_virtualized() -> None:
    plan = plan_launch(["server"], requested_env={"TOKEN": REFERENCE}, resolve=_resolve)
    env = plan.child_env()
    assert env["AGENTKEYS_VIRTUALIZED"] == "1"
    assert env["TOKEN"] == SCOPED
    assert plan.argv == ("server",)


def test_a_launch_plan_needs_a_command() -> None:
    with pytest.raises(ValueError, match="command"):
        plan_launch([], requested_env={}, resolve=_resolve)


def test_a_stock_stdio_server_starts_and_authenticates_with_no_secret_in_its_env(
    tmp_path: Path,
) -> None:
    """End to end: the broker spawns a JSON-RPC echo server whose env holds placeholders only."""
    report = tmp_path / "report.json"
    child = [
        sys.executable,
        "-c",
        (
            "import json, os, sys\n"
            f"report = {str(report)!r}\n"
            "line = sys.stdin.buffer.readline()\n"
            "token = os.environ.get('GITHUB_TOKEN', '')\n"
            "open(report, 'w').write(json.dumps({\n"
            "  'token': token,\n"
            "  'has_reference': 'akref:' in token,\n"
            "  'virtualized': os.environ.get('AGENTKEYS_VIRTUALIZED'),\n"
            "  'received': json.loads(line)['method'],\n"
            "}))\n"
            'sys.stdout.buffer.write(b\'{"jsonrpc":"2.0","id":1,"result":"ok"}\\n\')\n'
            "sys.stdout.buffer.flush()\n"
        ),
    ]
    plan = plan_launch(child, requested_env={"GITHUB_TOKEN": REFERENCE}, resolve=_resolve)
    stdout = io.BytesIO()
    code = run_under_broker(
        plan,
        stdin=io.BytesIO(b'{"jsonrpc":"2.0","id":1,"method":"initialize"}\n'),
        stdout=stdout,
        log=lambda line: None,
    )
    assert code == 0
    payload = json.loads(report.read_text())
    assert payload["token"] == SCOPED  # the server authenticated with a scoped token
    assert payload["has_reference"] is False  # no placeholder (and no long-lived secret) in its env
    assert payload["virtualized"] == "1"
    assert payload["received"] == "initialize"
    assert b'"result":"ok"' in stdout.getvalue()
