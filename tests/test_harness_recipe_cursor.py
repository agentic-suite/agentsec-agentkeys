"""10.4 — the Cursor recipe: same wrapper, header egress, an authenticated call (SC-36)."""

from __future__ import annotations

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.egress.contract import Injection
from agentkeys.recipes import get_recipe, render_mcp_wiring, run_recipe_smoke, validate_wiring
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
            harness="cursor",
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
        bindings=(("ref_1", "api.github.com", "gh"),),
        clock=lambda: 1000,
    )


def test_the_cursor_wiring_is_the_same_broker_wrapper() -> None:
    recipe = get_recipe("cursor")
    wiring = render_mcp_wiring(recipe, reference="akref:keychain/agentkeys/dev/token")
    validate_wiring(recipe, wiring)
    assert recipe.config_file == ".cursor/mcp.json"
    assert recipe.egress_kind == "header"


def test_the_cursor_smoke_ends_in_an_authenticated_call() -> None:
    core = _core()
    expected = core.resolve("ref_1", audience="api.github.com", tool="gh", session_id="s1").token
    assert expected is not None

    def target(injection: Injection) -> bool:
        return (injection.headers or {})["Authorization"] == f"Bearer {expected}"

    result = run_recipe_smoke(
        get_recipe("cursor"),
        core,
        session_id="s1",
        reference_id="ref_1",
        audience="api.github.com",
        tool="gh",
        target=target,
    )
    assert result.ok is True
    assert result.kind == "header"
    assert "ref_1" in result.transcript
    assert expected not in result.transcript
