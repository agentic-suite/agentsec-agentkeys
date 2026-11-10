"""6.2 — the kill-time harness: issue -> revoke -> replay-refused, p95 and max <= 1s."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentkeys.bench.killtime import PASS_BUDGET_MS, run_benchmark
from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore
from agentkeys.store.memory import MemoryStore
from agentkeys.store.sqlite import SqliteStore

TTL = {"dev": TtlBound(floor=30, ceiling=900)}
ITERATIONS = 100


def _core(store: MemoryStore | SqliteStore) -> ResolutionCore:
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


def test_kill_time_p95_and_max_are_within_one_second_memory() -> None:
    store = MemoryStore()
    store.open()
    report = run_benchmark(
        store,
        _core(store),
        reference_id="ref_1",
        audience="api.github.com",
        tool="gh",
        iterations=ITERATIONS,
    )
    assert report.iterations == ITERATIONS
    assert report.replay_failures == ITERATIONS
    assert report.p95_ms <= PASS_BUDGET_MS
    assert report.max_ms <= PASS_BUDGET_MS
    assert report.passed is True
    assert report.p50_ms <= report.p95_ms <= report.max_ms


def test_kill_time_p95_and_max_are_within_one_second_sqlite(tmp_path: Path) -> None:
    store = SqliteStore(tmp_path / "bench.db")
    store.open()
    try:
        report = run_benchmark(
            store,
            _core(store),
            reference_id="ref_1",
            audience="api.github.com",
            tool="gh",
            iterations=ITERATIONS,
        )
    finally:
        store.close()
    assert report.replay_failures == ITERATIONS
    assert report.p95_ms <= PASS_BUDGET_MS
    assert report.max_ms <= PASS_BUDGET_MS
    assert report.passed is True


def test_the_report_is_machine_readable() -> None:
    store = MemoryStore()
    store.open()
    report = run_benchmark(
        store,
        _core(store),
        reference_id="ref_1",
        audience="api.github.com",
        tool="gh",
        iterations=5,
    )
    payload = report.to_dict()
    assert payload["iterations"] == 5
    assert payload["budget_ms"] == PASS_BUDGET_MS
    assert {"p50_ms", "p95_ms", "max_ms", "passed", "replay_failures"} <= set(payload)


def test_a_benchmark_fails_loudly_when_the_replay_still_succeeds() -> None:
    store = MemoryStore()
    store.open()
    core = _core(store)

    class NeverRevokes:
        def revoke(self, *args: object, **kwargs: object) -> None:
            return None

    with pytest.raises(AssertionError, match="replay"):
        run_benchmark(
            store,
            core,
            reference_id="ref_1",
            audience="api.github.com",
            tool="gh",
            iterations=1,
            revoker=NeverRevokes(),  # type: ignore[arg-type]
        )
