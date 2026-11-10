"""Attack packs: context-dump, tamper, widening, spoof/replay (M11, WBS 11.4; release-blocking)."""

from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from agentkeys.contracts.registry import UnknownReference
from agentkeys.egress.contract import (
    AudienceMismatch,
    BaseInjector,
    InjectionRequest,
    WideningRefused,
)
from agentkeys.egress.header import HeaderInjector
from agentkeys.evidence import scan_text
from agentkeys.invariants import Context
from agentkeys.revoke import Revoker
from agentkeys.tamper import ConfigIntegrity, TamperError, TamperGuard

__all__ = ["PackResult", "run_attack_packs"]

InjectorFactory = Callable[[str], BaseInjector]


@dataclass(frozen=True)
class PackContext:
    """The live broker plus the injectors a pack exercises."""

    broker: Context
    injector_factory: InjectorFactory = HeaderInjector
    dump_extra: str = field(default="")


@dataclass(frozen=True)
class PackResult:
    """One attack pack's verdict."""

    name: str
    passed: bool
    detail: str


def _context_dump(pack: PackContext) -> str:
    broker = pack.broker
    resolved = broker.core.resolve(
        broker.reference_id,
        audience=broker.audience,
        tool=broker.tool,
        session_id=broker.session_id,
    )
    dump = json.dumps(
        {
            "references": [doc.to_dict() for doc in broker.core.list_references()],
            "issuance": resolved.issuance.to_dict(),
            "transcript": [broker.reference_id],
            "env": {"AGENTKEYS_HOME": "~/.agentkeys"},
            "extra": pack.dump_extra,
        }
    )
    if resolved.token is not None and resolved.token in dump:
        raise AssertionError("the dump contains a live token")
    findings = scan_text(dump, location="context-dump")
    if findings:
        classes = ", ".join(sorted({finding.class_ for finding in findings}))
        raise AssertionError(f"the dump contains credential shapes: {classes}")
    return "dump contains references only; no usable credential"


def _widening(pack: PackContext) -> str:
    broker = pack.broker
    resolved = broker.core.resolve(
        broker.reference_id,
        audience=broker.audience,
        tool=broker.tool,
        session_id=broker.session_id,
    )
    injector = pack.injector_factory(broker.audience)
    try:
        injector.apply(
            resolved,
            request=InjectionRequest(audience=broker.audience, tool="other-tool"),
        )
    except WideningRefused:
        pass
    else:
        raise AssertionError("a wider tool was injected")
    try:
        injector.apply(
            resolved,
            request=InjectionRequest(audience=broker.audience, tool=broker.tool, scope="admin"),
        )
    except WideningRefused:
        pass
    else:
        raise AssertionError("a wider scope was injected")
    try:
        injector.apply(
            resolved,
            request=InjectionRequest(audience="https://other.example", tool=broker.tool),
        )
    except AudienceMismatch:
        return "widening and wrong-audience injections refused"
    raise AssertionError("a wrong-audience injection was allowed")


def _spoof_replay(pack: PackContext) -> str:
    broker = pack.broker
    try:
        broker.core.resolve(
            "ref_invented",
            audience=broker.audience,
            tool=broker.tool,
            session_id=broker.session_id,
        )
    except UnknownReference:
        pass
    else:
        raise AssertionError("a spoofed reference was resolved")

    resolved = broker.core.resolve(
        broker.reference_id,
        audience=broker.audience,
        tool=broker.tool,
        session_id=broker.session_id,
    )
    assert resolved.token is not None
    first = broker.core.use(resolved.issuance.issuance_id, resolved.token, now=1001)
    replay = broker.core.use(resolved.issuance.issuance_id, resolved.token, now=1002)
    if first.status != "consumed" or replay.status == "consumed":
        raise AssertionError("a replayed token was accepted")
    return "spoofed reference refused; replay not accepted"


def _tamper(pack: PackContext) -> str:
    broker = pack.broker
    with tempfile.TemporaryDirectory() as directory:
        config = Path(directory) / "config.toml"
        config.write_text('enforce_mode = "enforce"\n', encoding="utf-8")
        integrity = ConfigIntegrity(config)
        integrity.pin()
        config.write_text('enforce_mode = "monitor"\n', encoding="utf-8")
        guard = TamperGuard(broker.store, integrity, clock=lambda: 1000)
        try:
            guard.check(session_id=broker.session_id)
        except TamperError:
            pass
        else:
            raise AssertionError("a tampered config was accepted")

    Revoker(broker.store, clock=lambda: 1000).revoke(
        "session", broker.session_id, reason="attack pack", requested_by="pack"
    )
    events = [row.event.event_name for row in broker.store.read_ledger()]
    if "tamper-detected" not in events or events[-1] != "revoked":
        raise AssertionError(f"tamper/revoke evidence missing: {events}")
    return "config tamper detected; revoke recorded"


def run_attack_packs(factory: Callable[[], PackContext]) -> tuple[PackResult, ...]:
    """Run every pack on a fresh broker; any failed assertion is a red pack."""
    packs = (
        ("context-dump", _context_dump),
        ("tamper", _tamper),
        ("widening", _widening),
        ("spoof-replay", _spoof_replay),
    )
    results: list[PackResult] = []
    for name, pack in packs:
        pack_context = factory()
        try:
            detail = pack(pack_context)
        except Exception as exc:
            results.append(PackResult(name, False, str(exc) or exc.__class__.__name__))
        else:
            results.append(PackResult(name, True, detail))
        finally:
            pack_context.broker.store.close()
    return tuple(results)
