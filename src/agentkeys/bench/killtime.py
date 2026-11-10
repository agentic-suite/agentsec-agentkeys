"""The kill-time benchmark (M6, WBS 6.2, SC-24): issue -> revoke -> replay refused.

The number the product is judged on is measured end-to-end, on the same monotonic clock domain,
and the *replay failure* — not a status flag — is the proof. PASS requires p95 <= 1s AND max <= 1s.
"""

from __future__ import annotations

import argparse
import json
import math
import time
import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agentkeys.config import TtlBound
from agentkeys.contracts.reference import ReferenceDoc
from agentkeys.contracts.registry import ReferenceRegistry
from agentkeys.core.resolution import ResolutionCore, ResolutionDenied
from agentkeys.revoke import Revoker
from agentkeys.store.contract import BrokerStore, Session

__all__ = ["PASS_BUDGET_MS", "KillTimeReport", "percentile", "run_benchmark"]

PASS_BUDGET_MS = 1000.0
_NS_PER_MS = 1_000_000


@dataclass(frozen=True)
class KillTimeReport:
    """The machine-readable kill-time result (PRD 17 §15)."""

    iterations: int
    p50_ms: float
    p95_ms: float
    max_ms: float
    replay_failures: int
    budget_ms: float = PASS_BUDGET_MS

    @property
    def passed(self) -> bool:
        """PASS only when both the p95 and the single worst case fit the budget."""
        return self.p95_ms <= self.budget_ms and self.max_ms <= self.budget_ms

    def to_dict(self) -> dict[str, float | int | bool]:
        return {
            "iterations": self.iterations,
            "p50_ms": self.p50_ms,
            "p95_ms": self.p95_ms,
            "max_ms": self.max_ms,
            "replay_failures": self.replay_failures,
            "budget_ms": self.budget_ms,
            "passed": self.passed,
        }


def percentile(values: Sequence[float], pct: float) -> float:
    """Nearest-rank percentile over a non-empty sample."""
    if not values:
        raise ValueError("percentile of an empty sample")
    ordered = sorted(values)
    rank = max(1, math.ceil(pct / 100.0 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _session(session_id: str) -> Session:
    return Session(
        session_id=session_id,
        agent_id="bench",
        harness="benchmark",
        started_at=0,
        ended_at=None,
        status="active",
        revoke_epoch=0,
        principal="bench",
    )


def run_benchmark(
    store: BrokerStore,
    core: ResolutionCore,
    *,
    reference_id: str,
    audience: str,
    tool: str,
    iterations: int = 100,
    principal: str = "benchmark",
    revoker: Revoker | None = None,
    monotonic_ns: Callable[[], int] | None = None,
) -> KillTimeReport:
    """Measure kill-time `iterations` times; a replay that still succeeds is a hard failure."""
    if iterations < 1:
        raise ValueError("iterations must be >= 1")
    clock_ns = monotonic_ns or time.monotonic_ns
    killer = revoker or Revoker(store)
    samples: list[float] = []
    failures = 0
    for _ in range(iterations):
        session_id = f"bench-{uuid.uuid4().hex}"
        store.create_session(_session(session_id))
        resolved = core.resolve(reference_id, audience=audience, tool=tool, session_id=session_id)
        t0 = clock_ns()
        killer.revoke("session", session_id, reason="benchmark", requested_by=principal)
        refused = False
        try:
            core.resolve(reference_id, audience=audience, tool=tool, session_id=session_id)
        except ResolutionDenied:
            refused = True
        if not refused:
            raise AssertionError(f"replay still resolves after revoke (session {session_id})")
        if resolved.token is not None:
            used = core.use(resolved.issuance.issuance_id, resolved.token)
            if used.status == "consumed":
                raise AssertionError(
                    f"replay token still authenticates after revoke (session {session_id})"
                )
        t1 = clock_ns()
        samples.append((t1 - t0) / _NS_PER_MS)
        failures += 1
    return KillTimeReport(
        iterations=iterations,
        p50_ms=percentile(samples, 50),
        p95_ms=percentile(samples, 95),
        max_ms=max(samples),
        replay_failures=failures,
    )


def _build_core(store: BrokerStore, reference_id: str, class_: str) -> ResolutionCore:
    registry = ReferenceRegistry(store)
    registry.register(
        ReferenceDoc(
            reference_id=reference_id,
            backend="file",
            path=f"agentkeys/bench/{reference_id}",
            class_=class_,
            label="benchmark reference (no secret)",
        ),
        created_by="benchmark",
    )
    bound = {class_: TtlBound(floor=30, ceiling=900)}
    return ResolutionCore(
        store,
        registry,
        ttl=bound,
        bindings=((reference_id, "bench.local", "bench"),),
        clock=lambda: 1000,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """`python -m agentkeys.bench.killtime` — JSON output so third parties can diff numbers."""
    parser = argparse.ArgumentParser(description="agentkeys kill-time benchmark (SC-24)")
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--reference", default="ref_bench")
    parser.add_argument("--class", dest="class_", default="dev")
    args = parser.parse_args(argv)

    from agentkeys.store.memory import MemoryStore

    store = MemoryStore()
    store.open()
    core = _build_core(store, args.reference, args.class_)
    report = run_benchmark(
        store,
        core,
        reference_id=args.reference,
        audience="bench.local",
        tool="bench",
        iterations=args.iterations,
    )
    print(json.dumps(report.to_dict(), sort_keys=True))
    return 0 if report.passed else 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
