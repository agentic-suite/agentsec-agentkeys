"""10.3 — the Claude Code recipe: same wrapper, env egress, an authenticated stdio call (SC-35)."""

from __future__ import annotations

import pytest

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.egress.contract import Injection
from agentkeys.egress.env import DEFAULT_VARIABLE
from agentkeys.recipes import (
    RECIPES,
    RecipeError,
    get_recipe,
    render_mcp_wiring,
    run_recipe_smoke,
    support_label,
    validate_wiring,
)
from agentkeys.store.contract import Session
from agentkeys.store.memory import MemoryStore

TTL = {"dev": TtlBound(floor=30, ceiling=900)}


def _core() -> ResolutionCore:
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id="s1",
            agent_id="a1",
            harness="claude-code",
            started_at=1,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )
    ReferenceRegistry(store).register(
        ReferenceDoc(
            reference_id="ref_1",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            label="dev token",
        )
    )
    return ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_1", "stdio.local", "stdio"),),
        clock=lambda: 1000,
    )


def test_the_claude_code_wiring_is_the_broker_wrapper() -> None:
    recipe = get_recipe("claude-code")
    wiring = render_mcp_wiring(recipe, reference="akref:keychain/agentkeys/dev/token")
    validate_wiring(recipe, wiring)
    entry = wiring["mcpServers"]["agentkeys"]
    assert entry["command"] == "agentkeys"
    assert entry["args"][:3] == ["run", "--server", "akref:keychain/agentkeys/dev/token"]
    assert entry["env"] == {}
    assert recipe.config_file == ".mcp.json"
    assert support_label(recipe).startswith("Claude Code: supported")


def test_the_claude_code_smoke_ends_in_an_authenticated_call() -> None:
    core = _core()
    expected = core.resolve("ref_1", audience="stdio.local", tool="stdio", session_id="s1").token
    assert expected is not None

    def target(injection: Injection) -> bool:
        return (injection.env or {})[DEFAULT_VARIABLE] == expected

    result = run_recipe_smoke(
        get_recipe("claude-code"),
        core,
        session_id="s1",
        reference_id="ref_1",
        audience="stdio.local",
        tool="stdio",
        target=target,
    )
    assert result.ok is True
    assert result.kind == "env"
    assert result.transcript == ("ref_1",)
    assert expected not in result.transcript


def test_a_wiring_that_bypasses_the_broker_is_refused() -> None:
    recipe = get_recipe("claude-code")
    wiring = render_mcp_wiring(recipe)
    wiring["mcpServers"]["agentkeys"]["command"] = "npx"
    with pytest.raises(RecipeError, match="broker wrapper"):
        validate_wiring(recipe, wiring)


def test_a_wiring_with_a_literal_secret_is_refused() -> None:
    recipe = get_recipe("claude-code")
    wiring = render_mcp_wiring(recipe)
    wiring["mcpServers"]["agentkeys"]["env"] = {"TOKEN": "sk-FAKE000000000000000000000000"}
    with pytest.raises(RecipeError, match="reference-only"):
        validate_wiring(recipe, wiring)


def test_reference_form_env_is_accepted() -> None:
    recipe = get_recipe("claude-code")
    wiring = render_mcp_wiring(recipe)
    wiring["mcpServers"]["agentkeys"]["env"] = {"UPSTREAM": "akref:keychain/agentkeys/dev/token"}
    validate_wiring(recipe, wiring)


def test_an_uncovered_harness_is_not_yet() -> None:
    recipe = get_recipe("jetbrains")
    assert recipe.supported is False
    assert "not yet" in support_label(recipe)
    with pytest.raises(RecipeError, match="not yet"):
        validate_wiring(recipe, render_mcp_wiring(recipe))


def test_every_tier_one_recipe_uses_the_same_command() -> None:
    commands = {
        render_mcp_wiring(RECIPES[name])["mcpServers"]["agentkeys"]["command"]
        for name in ("claude-code", "cursor")
    }
    # One command shape, one broker: no per-harness fork (E8).
    assert commands == {"agentkeys"}
    assert {RECIPES[name].egress_kind for name in ("claude-code", "cursor")} == {"env", "header"}
