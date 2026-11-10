"""12.5/12.6 — the revoke drill and append-only retention markers."""

from __future__ import annotations

import pytest

from agentkeys.invariants import AUDIENCE, TOOL, build_context
from agentkeys.ledger import verify_chain
from agentkeys.ops import RetentionPolicy, run_drill


def test_a_drill_reports_kill_time_numbers() -> None:
    ctx = build_context()
    try:
        report, generated_at = run_drill(
            ctx.store,
            ctx.core,
            reference_id="ref_1",
            audience=AUDIENCE,
            tool=TOOL,
            iterations=10,
            clock=lambda: 4242,
        )
    finally:
        ctx.store.close()
    assert report.iterations == 10
    assert report.replay_failures == 10
    assert report.passed is True
    assert generated_at == 4242
    assert {"p50_ms", "p95_ms", "max_ms"} <= set(report.to_dict())


def test_retention_appends_a_marker_and_deletes_nothing() -> None:
    ctx = build_context()
    try:
        ctx.core.resolve("ref_1", audience=AUDIENCE, tool=TOOL, session_id=ctx.session_id)
        before = ctx.store.read_ledger()
        event = RetentionPolicy(ctx.store).prune(1, actor="alice")
        after = ctx.store.read_ledger()
    finally:
        ctx.store.close()
    assert event.event_name == "retention-pruned"
    assert event.principal == "alice"
    assert "cutoff_seq=1" in (event.reason or "")
    assert len(after) == len(before) + 1
    assert after[: len(before)] == before
    assert verify_chain(after).intact is True


def test_retention_refuses_a_negative_cutoff() -> None:
    ctx = build_context()
    try:
        with pytest.raises(ValueError, match="before_seq"):
            RetentionPolicy(ctx.store).prune(-1)
    finally:
        ctx.store.close()
