"""5.4 - no token passthrough for stdio: the child never receives a client-supplied credential."""

from __future__ import annotations

import pytest

from agentkeys.stdio.substitute import (
    Substitution,
    assert_no_passthrough,
    build_virtualized_env,
    strip_client_credentials,
)

REFERENCE = "akref:keychain/agentkeys/dev/token"
CLIENT_SECRET = "client-supplied-github-token"


def _resolve(name: str, key: str) -> str:
    return "broker-minted-scoped-token"


@pytest.mark.parametrize(
    "name",
    ["GITHUB_TOKEN", "GH_TOKEN", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "DATABASE_URL"],
)
def test_client_credential_variables_are_stripped(name: str) -> None:
    env, stripped = strip_client_credentials({name: CLIENT_SECRET, "PATH": "/usr/bin"})
    assert name in stripped
    assert name not in env
    assert env["PATH"] == "/usr/bin"


def test_the_child_receives_a_broker_token_instead_of_the_client_token() -> None:
    substitution = build_virtualized_env(
        {"GITHUB_TOKEN": CLIENT_SECRET, "API_TOKEN": REFERENCE}, resolve=_resolve
    )
    assert "GITHUB_TOKEN" not in substitution.env
    assert substitution.env["API_TOKEN"] == "broker-minted-scoped-token"
    assert CLIENT_SECRET not in "\x00".join(substitution.env.values())
    assert substitution.stripped == ("GITHUB_TOKEN",)


def test_a_stripped_credential_is_recorded_as_a_receipt() -> None:
    substitution = build_virtualized_env({"GITHUB_TOKEN": CLIENT_SECRET}, resolve=_resolve)
    assert any(draft.class_ == "stripped-client-credential" for draft in substitution.receipts)


def test_the_passthrough_guard_fires_if_a_client_value_reaches_the_child() -> None:
    substitution = Substitution(
        env={"GITHUB_TOKEN": CLIENT_SECRET}, replaced=(), stripped=(), receipts=()
    )
    with pytest.raises(Exception, match="client credential reached the child"):
        assert_no_passthrough(substitution.env, CLIENT_SECRET)


def test_the_passthrough_guard_is_quiet_when_the_child_holds_a_broker_token() -> None:
    assert_no_passthrough({"API_TOKEN": "broker-minted-scoped-token"}, CLIENT_SECRET)
