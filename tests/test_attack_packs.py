"""11.4 — the four attack packs pass, and a broken gate turns a pack red (SC-40/SC-41/SC-42)."""

from __future__ import annotations

from agentkeys.attackpacks import PackContext, run_attack_packs
from agentkeys.backends.contract import SecretValue
from agentkeys.correlation import join_keys
from agentkeys.egress.contract import BaseInjector, Injection, InjectionRequest
from agentkeys.invariants import build_context


def _pack() -> PackContext:
    return PackContext(broker=build_context())


def test_every_attack_pack_passes() -> None:
    results = run_attack_packs(_pack)
    assert {result.name for result in results} == {
        "context-dump",
        "tamper",
        "widening",
        "spoof-replay",
    }
    failed = [(result.name, result.detail) for result in results if not result.passed]
    assert failed == []


def test_a_leaky_context_dump_turns_the_pack_red() -> None:
    def leaky() -> PackContext:
        return PackContext(
            broker=build_context(), dump_extra="sk-FAKE000000000000000000000000000000000000"
        )

    results = {result.name: result for result in run_attack_packs(leaky)}
    assert results["context-dump"].passed is False
    assert "credential shapes" in results["context-dump"].detail


def test_a_permissive_injector_turns_the_widening_pack_red() -> None:
    class Permissive(BaseInjector):
        kind = "permissive"

        def _check(self, resolved: object, request: object, now: object) -> None:
            return None

        def _deliver(self, resolved: object, request: InjectionRequest) -> Injection:
            return Injection(
                kind=self.kind,
                audience=self.target_audience(),
                secret=SecretValue("token"),
                headers={"Authorization": "Bearer token"},
            )

    def permissive() -> PackContext:
        return PackContext(broker=build_context(), injector_factory=Permissive)

    results = {result.name: result for result in run_attack_packs(permissive)}
    assert results["widening"].passed is False
    assert "tool" in results["widening"].detail


def test_join_keys_cover_the_attack_evidence() -> None:
    ctx = build_context()
    try:
        ctx.store.append_event(
            __import__("agentkeys.events", fromlist=["build_event"]).build_event(
                "evasion-detected", occurred_at=1, session_id="s1", reason="attack"
            )
        )
        row = ctx.store.read_ledger()[-1]
        assert join_keys(row)["session_id"] == "s1"
    finally:
        ctx.store.close()
