"""The store conformance suite — the contract's executable form (M1, WBS 1.4).

`run_conformance(factory)` returns findings; an empty list means the driver honours the six semantics
(S1-S6) in `docs/design/v0.1.0/store.md` §5. The suite is deliberately strict: a broken driver must fail
it, which the tests prove with the fakes in `conformance_fakes.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace

from agentkeys.store import contract as c

__all__ = ["Finding", "run_conformance"]

Factory = Callable[[], c.BrokerStore]
"""A zero-argument store factory bound to one check's namespace (see `run_conformance`)."""

_NamespaceFactory = Callable[[str], c.BrokerStore]
"""The caller's factory: given a namespace key, return a store isolated to that key."""

_CHECKS: list[Callable[[Factory, list[Finding]], None]] = []


@dataclass(frozen=True)
class Finding:
    """One conformance failure: the check that failed and why."""

    check: str
    detail: str


def check(
    function: Callable[[Factory, list[Finding]], None],
) -> Callable[[Factory, list[Finding]], None]:
    _CHECKS.append(function)
    return function


def _expect(condition: bool, findings: list[Finding], check_name: str, detail: str) -> None:
    if not condition:
        findings.append(Finding(check=check_name, detail=detail))


def _event(event_id: str, issuance_id: str | None = None, session_id: str = "s1") -> c.LedgerEvent:
    return c.LedgerEvent(
        event_id=event_id,
        event_version="1.0",
        event_name="issuance.created",
        occurred_at=1000,
        monotonic_ms=5,
        session_id=session_id,
        agent_id="a1",
        reference_id="ref_1",
        issuance_id=issuance_id,
        binding_json="{}",
        ttl_seconds=60,
        principal="op",
        reason=None,
        severity="info",
    )


def _seed(store: c.BrokerStore) -> None:
    store.create_reference(
        c.Reference(
            reference_id="ref_1",
            akref_version="1.0",
            backend="keychain",
            path="agentkeys/dev/token",
            class_="dev",
            scope_hint=None,
            label=None,
            created_at=1000,
            created_by="op",
        )
    )
    store.create_session(
        c.Session(
            session_id="s1",
            agent_id="a1",
            harness="claude-code",
            started_at=900,
            ended_at=None,
            status="active",
            revoke_epoch=0,
            principal="op",
        )
    )


def _issue(
    store: c.BrokerStore,
    *,
    binding_hash: str = "bh_1",
    window: int = 1,
    event_id: str = "e1",
    ttl: int = 60,
    issued_at: int = 1000,
) -> c.Issuance:
    return store.issue(
        reference_id="ref_1",
        session_id="s1",
        agent_id="a1",
        audience="api.github.com",
        tool="gh",
        class_="dev",
        ttl_seconds=ttl,
        window=window,
        secret_hash="hash_1",
        single_use=True,
        issued_at=issued_at,
        provenance_json="{}",
        binding_hash=binding_hash,
        event=_event(event_id),
    )


@check
def capabilities_are_declared(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        flags = store.capabilities()
        _expect(
            isinstance(flags, c.CapabilityFlags), findings, "capabilities", "not CapabilityFlags"
        )
        _expect(flags.atomic_issue, findings, "capabilities", "atomic_issue must be True")
    finally:
        store.close()


@check
def capability_refusal_is_enforced(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        try:
            c.require_capabilities(store.capabilities(), ("cluster_safe",))
            findings.append(
                Finding("capability_refusal", "require_capabilities must refuse missing flags")
            )
        except c.CapabilityError:
            pass
    finally:
        store.close()


@check
def references_are_idempotent(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        reference = store.get_reference("ref_1")
        _expect(reference is not None, findings, "references", "reference not stored")
        if reference is None:  # pragma: no cover - guarded by the check above
            return
        try:
            store.create_reference(replace(reference, backend="file"))
            findings.append(Finding("references", "conflicting reference was accepted"))
        except c.StoreError:
            pass
    finally:
        store.close()


@check
def issue_is_idempotent_per_binding_and_window(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        first = _issue(store, event_id="e1")
        second = _issue(store, event_id="e2")
        _expect(
            first.issuance_id == second.issuance_id,
            findings,
            "issue_idempotency",
            "retry minted a new issuance",
        )
        binding = store.get_binding("bh_1")
        _expect(
            binding is not None and binding.issuance_count == 1,
            findings,
            "issue_idempotency",
            "issuance_count double-counted a retry",
        )
        issuance_events = [
            row for row in store.read_ledger() if row.event.event_name == "issuance.created"
        ]
        _expect(
            len(issuance_events) == 1,
            findings,
            "issue_idempotency",
            "retry appended an extra issuance event",
        )
        third = _issue(store, window=2, event_id="e3")
        _expect(
            third.issuance_id != first.issuance_id,
            findings,
            "issue_idempotency",
            "a new window must mint a new issuance",
        )
    finally:
        store.close()


@check
def consume_is_single_use(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        issuance = _issue(store)
        _expect(
            store.consume(issuance.issuance_id, now=1001).status == "consumed",
            findings,
            "consume",
            "first consume must succeed",
        )
        again = store.consume(issuance.issuance_id, now=1002)
        _expect(
            again.status == "already_consumed",
            findings,
            "consume",
            "second consume must be already_consumed",
        )
        _expect(
            store.consume("iss_missing", now=1002).status == "unknown",
            findings,
            "consume",
            "unknown id must be unknown",
        )
    finally:
        store.close()


@check
def expiry_is_enforced(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        issuance = _issue(store, ttl=60, issued_at=1000)
        result = store.consume(issuance.issuance_id, now=1061)
        _expect(result.status == "expired", findings, "expiry", "expired issuance was consumable")
        _expect(
            result.issuance is not None and result.issuance.consumed_at is None,
            findings,
            "expiry",
            "expired issuance must not be marked consumed",
        )
    finally:
        store.close()


@check
def live_reads_exclude_consumed_and_expired(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        live = _issue(store, binding_hash="bh_live", event_id="e1")
        _issue(store, binding_hash="bh_other", window=2, event_id="e2", ttl=1)
        matching = [i.issuance_id for i in store.list_live(now=1001)]
        _expect(live.issuance_id in matching, findings, "list_live", "live issuance missing")
        _expect(len(matching) == 1, findings, "list_live", "expired issuance reported live")
    finally:
        store.close()


@check
def revoke_has_one_winner_and_a_monotonic_epoch(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        first = store.cas_revoke(
            scope="session",
            target_id="s1",
            requested_by="op",
            requested_at=1100,
            reason="operator",
            event=_event("rev1"),
        )
        second = store.cas_revoke(
            scope="session",
            target_id="s1",
            requested_by="op2",
            requested_at=1101,
            reason="again",
            event=_event("rev2"),
        )
        _expect(first.winner and not second.winner, findings, "cas_revoke", "CAS winner wrong")
        _expect(
            first.epoch_after == first.epoch_before + 1,
            findings,
            "cas_revoke",
            "epoch must advance by one",
        )
        _expect(
            second.revocation.revocation_id == first.revocation.revocation_id,
            findings,
            "cas_revoke",
            "loser must return the winner's revocation",
        )
        revoke_events = [row for row in store.read_ledger() if row.event.event_id.startswith("rev")]
        _expect(len(revoke_events) == 1, findings, "cas_revoke", "loser appended an event")
        try:
            store.cas_revoke(
                scope="session",
                target_id="ghost",
                requested_by="op",
                requested_at=1,
                reason="r",
                event=_event("rev3"),
            )
            findings.append(Finding("cas_revoke", "unknown target must error"))
        except c.StoreError:
            pass
    finally:
        store.close()


@check
def ledger_is_gapless_and_hash_chained(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        _seed(store)
        store.append_event(_event("a"))
        store.append_event(_event("b"))
        rows = store.read_ledger()
        seqs = [row.seq for row in rows]
        _expect(seqs == list(range(1, len(seqs) + 1)), findings, "ledger", f"gap in seq: {seqs}")
        _expect(rows[0].prev_hash == c.GENESIS_PREV_HASH, findings, "ledger", "bad genesis anchor")
        previous = c.GENESIS_PREV_HASH
        for row in rows:
            if row.prev_hash != previous or row.hash != c.compute_hash(row.event, previous):
                findings.append(Finding("ledger", f"chain broken at seq {row.seq}"))
                break
            previous = row.hash
        try:
            store.append_event(_event("a"))
            findings.append(Finding("ledger", "duplicate event_id accepted"))
        except c.StoreError:
            pass
        scoped = store.export_session("s1")
        _expect(
            all(row.event.session_id == "s1" for row in scoped),
            findings,
            "ledger",
            "export_session leaked another session",
        )
    finally:
        store.close()


@check
def receipts_round_trip(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        receipt = c.RedactionReceipt(
            receipt_id="rcpt_1",
            subject_id="iss_1",
            field="authorization",
            class_="bearer",
            count=1,
            redactor_version="1.0",
            created_at=1,
        )
        store.add_receipt(receipt)
        _expect(
            store.list_receipts("iss_1") == (receipt,),
            findings,
            "receipts",
            "receipt did not round-trip",
        )
    finally:
        store.close()


@check
def declared_durability_is_honest(factory: Factory, findings: list[Finding]) -> None:
    store = factory()
    store.open()
    try:
        durable = store.capabilities().durable
        _seed(store)
        if not durable:
            return
        reopened = factory()
        reopened.open()
        try:
            _expect(
                reopened.get_reference("ref_1") is not None,
                findings,
                "durability",
                "durable driver lost data across instances",
            )
        finally:
            reopened.close()
    finally:
        store.close()


def run_conformance(factory: _NamespaceFactory) -> list[Finding]:
    """Run every check against stores from `factory`, each isolated by its own namespace key."""
    findings: list[Finding] = []
    for index, function in enumerate(_CHECKS):
        key = f"{index:02d}-{function.__name__}"

        def bound(_key: str = key) -> c.BrokerStore:
            return factory(_key)

        try:
            function(bound, findings)
        except Exception as exc:  # a crashing driver is a finding, not a test error
            findings.append(Finding(check=function.__name__, detail=f"raised {exc!r}"))
    return findings
