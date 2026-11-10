"""11.3 — every invariant I1-I10 holds, and a violated context goes red."""

from __future__ import annotations

from typing import Any

import pytest

import agentkeys.invariants as invariants
from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolvedIssuance
from agentkeys.invariants import INVARIANTS, Context, build_context, run_invariants
from agentkeys.store.memory import MemoryStore


def test_every_invariant_holds() -> None:
    results = run_invariants()
    assert len(results) == 10
    broken = [invariant.id for invariant, ok in results if not ok]
    assert broken == []


def test_the_runner_reports_a_failure() -> None:
    def broken_context() -> Context:
        ctx = build_context()
        ctx.store.close()
        return ctx

    results = run_invariants(broken_context)
    assert any(not ok for _invariant, ok in results)


def test_i2_goes_red_when_an_unknown_reference_resolves() -> None:
    ctx = build_context()

    class PermissiveCore:
        def resolve(self, *args: Any, **kwargs: Any) -> ResolvedIssuance:
            real = ctx.core.resolve(
                "ref_1", audience=ctx.audience, tool=ctx.tool, session_id=ctx.session_id
            )
            return real

    with pytest.raises(AssertionError):
        _invariant("I2").probe(replace_context(ctx, core=PermissiveCore()))
    ctx.store.close()


def test_i4_goes_red_when_revoke_does_not_kill() -> None:
    class NoRevokeStore(MemoryStore):
        def cas_revoke(self, **kwargs: Any) -> Any:
            from agentkeys.store.contract import Revocation, RevokeResult

            revocation = Revocation(
                revocation_id="rev_fake",
                scope=kwargs["scope"],
                target_id=kwargs["target_id"],
                requested_by=kwargs["requested_by"],
                requested_at=kwargs["requested_at"],
                effective_at=kwargs["requested_at"],
                reason=kwargs["reason"],
                epoch_after=1,
            )
            return RevokeResult(revocation=revocation, winner=True, epoch_before=0, epoch_after=1)

    store = NoRevokeStore()
    store.open()
    store.create_session(invite_session())
    ReferenceRegistry(store).register(
        ReferenceDoc(
            reference_id="ref_1",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            label="dev token",
        )
    )
    core = ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl={"dev": TtlBound(30, 900)},
        bindings=(("ref_1", "https://api.example.com", "call"),),
        clock=lambda: 1000,
    )
    ctx = Context(store=store, core=core)
    with pytest.raises(AssertionError):
        _invariant("I4").probe(ctx)
    store.close()


def test_i6_goes_red_when_a_wrong_audience_is_allowed() -> None:
    ctx = build_context()
    permissive = ResolutionCore(
        ctx.store,
        ReferenceRegistry(ctx.store),
        ttl={"dev": TtlBound(30, 900)},
        bindings=(("ref_1", "https://other.example", "call"), ("ref_1", ctx.audience, "call")),
        clock=lambda: 1000,
    )
    with pytest.raises(AssertionError):
        _invariant("I6").probe(replace_context(ctx, core=permissive))
    ctx.store.close()


def test_i10_goes_red_when_the_verifier_is_blind(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BlindReport:
        intact = True

    monkeypatch.setattr(invariants, "verify_chain", lambda rows: BlindReport())
    ctx = build_context()
    with pytest.raises(AssertionError):
        _invariant("I10").probe(ctx)
    ctx.store.close()


def _invariant(identifier: str) -> Any:
    return next(invariant for invariant in INVARIANTS if invariant.id == identifier)


def replace_context(ctx: Context, **changes: Any) -> Context:
    return Context(
        store=changes.get("store", ctx.store),
        core=changes.get("core", ctx.core),
        reference_id=ctx.reference_id,
        session_id=ctx.session_id,
        audience=ctx.audience,
        tool=ctx.tool,
    )


def invite_session() -> Any:
    from agentkeys.store.contract import Session

    return Session(
        session_id="s1",
        agent_id="a1",
        harness="claude-code",
        started_at=1,
        ended_at=None,
        status="active",
        revoke_epoch=0,
        principal="op",
    )
