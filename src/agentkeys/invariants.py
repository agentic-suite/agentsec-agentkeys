"""Invariants I1-I10 as executable probes, each with a red-when-violated fixture (M11, 11.3)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry, UnknownReference
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.egress.contract import InjectionRequest
from agentkeys.egress.header import HeaderInjector
from agentkeys.ledger import verify_chain
from agentkeys.revoke import Revoker
from agentkeys.store.contract import Session, canonical_event_json
from agentkeys.store.memory import MemoryStore

__all__ = ["INVARIANTS", "Context", "Invariant", "build_context", "run_invariants"]

AUDIENCE = "https://api.example.com"
TOOL = "call"
SESSION = "s1"
TTL = {"dev": TtlBound(floor=30, ceiling=900)}


@dataclass
class Context:
    """One live broker context an invariant probes."""

    store: MemoryStore
    core: ResolutionCore
    reference_id: str = "ref_1"
    session_id: str = SESSION
    audience: str = AUDIENCE
    tool: str = TOOL


def build_context() -> Context:
    """A fresh in-memory broker with one session and one allowed binding."""
    store = MemoryStore()
    store.open()
    store.create_session(
        Session(
            session_id=SESSION,
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
    core = ResolutionCore(
        store,
        ReferenceRegistry(store),
        ttl=TTL,
        bindings=(("ref_1", AUDIENCE, TOOL),),
        clock=lambda: 1000,
    )
    return Context(store=store, core=core)


def _resolve(ctx: Context) -> str:
    resolved = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=ctx.session_id
    )
    assert resolved.token is not None
    return resolved.token


def _i1_never_in_context(ctx: Context) -> None:
    resolved = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=ctx.session_id
    )
    rendered = resolved.issuance.to_json()
    assert resolved.token is None or resolved.token not in rendered
    assert "token" not in resolved.issuance.to_dict()


def _i2_fail_closed(ctx: Context) -> None:
    try:
        ctx.core.resolve("ref_missing", audience=ctx.audience, tool=ctx.tool, session_id=SESSION)
    except UnknownReference:
        return
    raise AssertionError("an unknown reference was resolved")


def _i3_single_use(ctx: Context) -> None:
    resolved = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=SESSION
    )
    assert resolved.token is not None
    first = ctx.core.use(resolved.issuance.issuance_id, resolved.token, now=1001)
    second = ctx.core.use(resolved.issuance.issuance_id, resolved.token, now=1002)
    assert first.status == "consumed"
    assert second.status != "consumed"


def _i4_revoke(ctx: Context) -> None:
    Revoker(ctx.store, clock=lambda: 1000).revoke(
        "session", SESSION, reason="test", requested_by="op"
    )
    try:
        ctx.core.resolve(ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=SESSION)
    except ResolutionDenied:
        return
    raise AssertionError("a revoked session resolved")


def _i5_no_secret_at_rest(ctx: Context) -> None:
    token = _resolve(ctx)
    ledger_text = "\x00".join(canonical_event_json(row.event) for row in ctx.store.read_ledger())
    assert token not in ledger_text
    assert all(token not in (row.event.reason or "") for row in ctx.store.read_ledger())


def _i6_audience(ctx: Context) -> None:
    try:
        ctx.core.resolve(
            ctx.reference_id, audience="https://other.example", tool=ctx.tool, session_id=SESSION
        )
    except ResolutionDenied:
        return
    raise AssertionError("a wrong-audience binding was allowed")


def _i7_session(ctx: Context) -> None:
    ctx.store.create_session(
        Session(
            session_id="s2",
            agent_id="a2",
            harness="cursor",
            started_at=1,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )
    first = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=SESSION
    )
    second = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id="s2"
    )
    assert first.token != second.token


def _i8_no_passthrough(ctx: Context) -> None:
    resolved = ctx.core.resolve(
        ctx.reference_id, audience=ctx.audience, tool=ctx.tool, session_id=SESSION
    )
    injector = HeaderInjector(ctx.audience)
    injection = injector.apply(
        resolved,
        request=InjectionRequest(
            audience=ctx.audience,
            tool=ctx.tool,
            client_token="client-token",
            client_headers={"Authorization": "Bearer client-token"},
        ),
    )
    headers = "\x00".join((injection.headers or {}).values())
    assert "client-token" not in headers


def _i9_chain(ctx: Context) -> None:
    _resolve(ctx)
    report = verify_chain(ctx.store.read_ledger())
    assert report.intact is True


def _i10_tamper(ctx: Context) -> None:
    _resolve(ctx)
    rows = list(ctx.store.read_ledger())
    rows[0] = replace(rows[0], event=replace(rows[0].event, reason="rewritten"))
    assert verify_chain(tuple(rows)).intact is False


@dataclass(frozen=True)
class Invariant:
    """One named invariant and its probe (a violation raises)."""

    id: str
    statement: str
    probe: Callable[[Context], None]


INVARIANTS: tuple[Invariant, ...] = (
    Invariant("I1", "no secret in agent context", _i1_never_in_context),
    Invariant("I2", "fail closed on an unknown reference", _i2_fail_closed),
    Invariant("I3", "issuance secrets are single-use", _i3_single_use),
    Invariant("I4", "revocation kills resolution", _i4_revoke),
    Invariant("I5", "no plaintext secret at rest", _i5_no_secret_at_rest),
    Invariant("I6", "audience binding is enforced", _i6_audience),
    Invariant("I7", "session binding is enforced", _i7_session),
    Invariant("I8", "no client-token passthrough", _i8_no_passthrough),
    Invariant("I9", "the ledger chain verifies", _i9_chain),
    Invariant("I10", "a rewritten ledger row is detected", _i10_tamper),
)


def run_invariants(
    factory: Callable[[], Context] = build_context,
) -> tuple[tuple[Invariant, bool], ...]:
    """Run each invariant on a fresh context; `True` means it holds."""
    results: list[tuple[Invariant, bool]] = []
    for invariant in INVARIANTS:
        ctx = factory()
        try:
            invariant.probe(ctx)
        except Exception:
            results.append((invariant, False))
        else:
            results.append((invariant, True))
        finally:
            ctx.store.close()
    return tuple(results)
