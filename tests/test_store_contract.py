"""1.1 — the typed BrokerStore contract: records, capabilities, errors, chain hashing."""

from __future__ import annotations

import dataclasses
from typing import get_type_hints

import pytest

from agentkeys.store import contract as c


def test_records_are_frozen_dataclasses() -> None:
    for record in (
        c.CapabilityFlags,
        c.Reference,
        c.Session,
        c.Binding,
        c.Issuance,
        c.Revocation,
        c.LedgerEvent,
        c.LedgerRow,
        c.RedactionReceipt,
        c.ConsumeResult,
    ):
        assert dataclasses.is_dataclass(record), record
        params = getattr(record, "__dataclass_params__", None)
        assert params is not None and params.frozen, record


def test_reference_has_no_secret_field() -> None:
    fields = set(get_type_hints(c.Reference))
    assert {"reference_id", "akref_version", "backend", "path", "class_"} <= fields
    assert not any("secret" in name and name != "secret_hash" for name in fields)


def test_issuance_carries_only_a_secret_hash() -> None:
    fields = set(get_type_hints(c.Issuance))
    assert "secret_hash" in fields
    assert "secret" not in fields
    assert "plaintext" not in fields


def test_capability_flags_are_all_bool() -> None:
    hints = get_type_hints(c.CapabilityFlags)
    assert set(hints) == {"single_writer", "durable", "atomic_issue", "cluster_safe"}
    assert all(hint is bool for hint in hints.values())


def test_consume_result_is_a_typed_state() -> None:
    result = c.ConsumeResult(status="consumed", issuance=None)
    assert result.status == "consumed"
    assert c.ConsumeStatus is not None


def test_protocol_declares_every_contract_method() -> None:
    expected = {
        "capabilities",
        "open",
        "close",
        "create_reference",
        "get_reference",
        "list_references",
        "create_session",
        "get_session",
        "issue",
        "get_issuance",
        "find_issuance",
        "consume",
        "list_live",
        "cas_revoke",
        "get_revocation",
        "append_event",
        "read_ledger",
        "export_session",
        "add_receipt",
        "list_receipts",
    }
    assert expected <= set(dir(c.BrokerStore))


def test_capability_refusal_names_the_missing_flag() -> None:
    flags = c.CapabilityFlags(
        single_writer=True, durable=False, atomic_issue=True, cluster_safe=False
    )
    with pytest.raises(c.CapabilityError, match="durable"):
        c.require_capabilities(flags, ("atomic_issue", "durable"))
    c.require_capabilities(flags, ("atomic_issue", "single_writer"))


def test_genesis_anchor_and_chain_hashing() -> None:
    event = c.LedgerEvent(
        event_id="evt_1",
        event_version="1.0",
        event_name="issuance.created",
        occurred_at=1000,
        monotonic_ms=5,
        session_id="s1",
        agent_id="a1",
        reference_id="ref_1",
        issuance_id="iss_1",
        binding_json="{}",
        ttl_seconds=60,
        principal="op",
        reason=None,
        severity="info",
    )
    assert c.GENESIS_PREV_HASH == "0" * 64
    first = c.compute_hash(event, c.GENESIS_PREV_HASH)
    assert len(first) == 64
    assert first == c.compute_hash(event, c.GENESIS_PREV_HASH)  # deterministic
    assert first != c.compute_hash(event, "f" * 64)  # bound to the previous row
    other = dataclasses.replace(event, event_id="evt_2")
    assert first != c.compute_hash(other, c.GENESIS_PREV_HASH)


def test_canonical_event_json_is_ordered_and_stable() -> None:
    event = c.LedgerEvent(
        event_id="evt_1",
        event_version="1.0",
        event_name="issuance.created",
        occurred_at=1000,
        monotonic_ms=5,
        session_id=None,
        agent_id=None,
        reference_id=None,
        issuance_id=None,
        binding_json=None,
        ttl_seconds=None,
        principal=None,
        reason=None,
        severity="info",
    )
    assert c.canonical_event_json(event) == c.canonical_event_json(dataclasses.replace(event))


def test_error_hierarchy() -> None:
    for error in (
        c.CapabilityError,
        c.StoreVersionError,
        c.StoreBusyError,
        c.DriverNotFound,
        c.DriverError,
    ):
        assert issubclass(error, c.StoreError)
