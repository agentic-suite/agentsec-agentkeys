"""11.2 — the evidence scanner finds zero secrets, and a seeded leak fails the build (SC-43)."""

from __future__ import annotations

from agentkeys.events import build_event
from agentkeys.evidence import scan_evidence, scan_text
from agentkeys.invariants import build_context
from agentkeys.store.contract import RedactionReceipt


def test_a_clean_store_passes() -> None:
    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=ctx.audience, tool=ctx.tool, session_id=ctx.session_id)
        report = scan_evidence(ctx.store)
    finally:
        ctx.store.close()
    assert report.ok is True
    assert report.rows >= 2
    assert report.findings == ()


def test_a_seeded_leak_fails_with_the_row() -> None:
    ctx = build_context()
    try:
        ctx.store.append_event(
            build_event(
                "exchange-rejected",
                occurred_at=1000,
                session_id=ctx.session_id,
                reason="sk-FAKE000000000000000000000000000000000000",
            )
        )
        report = scan_evidence(ctx.store)
    finally:
        ctx.store.close()
    assert report.ok is False
    assert report.findings
    assert report.findings[0].location.startswith("ledger:")


def test_scan_text_reports_the_class_not_the_value() -> None:
    findings = scan_text("token=ghp_FAKE0000000000000000000000000000000000", location="x")
    assert findings
    assert findings[0].class_ == "api-key"
    assert findings[0].length > 0
    assert not hasattr(findings[0], "value")


def test_receipts_are_counted() -> None:
    ctx = build_context()
    try:
        ctx.store.add_receipt(
            RedactionReceipt(
                receipt_id="rec_1",
                subject_id="s1",
                field="args",
                class_="api-key",
                count=1,
                redactor_version="1.0",
                created_at=1000,
            )
        )
        report = scan_evidence(ctx.store)
    finally:
        ctx.store.close()
    assert report.receipts == 1
    assert report.ok is True
