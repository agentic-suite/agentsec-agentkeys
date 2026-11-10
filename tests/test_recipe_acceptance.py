"""10.5/10.6 — generic recipes, the acceptance harness, and honest "not yet" (SC-37/SC-38)."""

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


def _core() -> ResolutionCore:
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id="s1",
            agent_id="a1",
            harness="generic",
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
        ttl={"dev": TtlBound(30, 900)},
        bindings=(("ref_1", "api.example.com", "call"),),
        clock=lambda: 1000,
    )


def test_the_generic_recipes_are_declared() -> None:
    for name in ("generic-mcp", "generic-http", "generic-exchange", "generic-cli"):
        assert get_recipe(name).supported is True
        validate_wiring(get_recipe(name), render_mcp_wiring(get_recipe(name)))


def test_a_generic_smoke_authenticates() -> None:
    core = _core()
    expected = core.resolve("ref_1", audience="api.example.com", tool="call", session_id="s1").token

    def target(injection: Injection) -> bool:
        return (injection.env or {})[DEFAULT_VARIABLE] == expected

    result = run_recipe_smoke(
        get_recipe("generic-mcp"),
        core,
        session_id="s1",
        reference_id="ref_1",
        audience="api.example.com",
        tool="call",
        target=target,
    )
    assert result.ok is True


def test_a_missing_wiring_fails_the_harness() -> None:
    with pytest.raises(RecipeError):
        validate_wiring(get_recipe("claude-code"), {})


def test_an_unknown_recipe_is_refused() -> None:
    with pytest.raises(RecipeError, match="unknown recipe"):
        get_recipe("no-such-harness")


def test_an_uncovered_harness_is_labelled_not_yet() -> None:
    assert "not yet" in support_label(RECIPES["jetbrains"])
    assert "not yet" not in support_label(RECIPES["claude-code"])


def test_a_smoke_for_an_unsupported_egress_fails_honestly() -> None:
    core = _core()
    with pytest.raises(RecipeError, match="exchange"):
        run_recipe_smoke(
            get_recipe("generic-exchange"),
            core,
            session_id="s1",
            reference_id="ref_1",
            audience="api.example.com",
            tool="call",
            target=lambda injection: True,
        )
