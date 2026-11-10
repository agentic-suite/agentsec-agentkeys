"""1.4 — the conformance suite passes real drivers and fails deliberately broken ones."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from agentkeys.store import contract as c
from agentkeys.store.memory import MemoryStore
from agentkeys.store.sqlite import SqliteStore
from tests.conformance_fakes import AmoebaStore, GappedLedger, LooseConsume, NonIdempotentIssue
from tests.store_conformance import run_conformance

Factory = Callable[[], c.BrokerStore]


@pytest.fixture(params=["sqlite-file", "sqlite-memory", "memory"])
def good_factory(request: pytest.FixtureRequest, tmp_path: Path) -> Callable[[str], c.BrokerStore]:
    if request.param == "sqlite-file":
        return lambda key: SqliteStore(tmp_path / f"{key}.db")
    if request.param == "sqlite-memory":
        return lambda key: SqliteStore(":memory:")
    return lambda key: MemoryStore()


def test_real_drivers_conform(good_factory: Callable[[str], c.BrokerStore]) -> None:
    findings = run_conformance(good_factory)
    assert findings == [], findings


@pytest.mark.parametrize(
    ("fake", "expected_check"),
    [
        (NonIdempotentIssue, "issue_idempotency"),
        (GappedLedger, "ledger"),
        (LooseConsume, "consume"),
        (AmoebaStore, "durability"),
    ],
)
def test_broken_drivers_fail_the_suite(
    fake: Callable[[], MemoryStore], expected_check: str
) -> None:
    findings = run_conformance(lambda key: fake())
    assert findings, f"{fake.__name__} passed a suite it must fail"
    assert expected_check in {finding.check for finding in findings}


def test_suite_reports_the_failing_check_name() -> None:
    findings = run_conformance(lambda key: NonIdempotentIssue())
    assert all(finding.detail for finding in findings)
