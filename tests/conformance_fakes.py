"""Deliberately broken drivers: the conformance suite must report a finding for each (WBS 1.4)."""

from __future__ import annotations

import uuid

from agentkeys.store.contract import CapabilityFlags, ConsumeResult, Issuance, LedgerRow
from agentkeys.store.memory import MemoryStore

__all__ = ["AmoebaStore", "GappedLedger", "LooseConsume", "NonIdempotentIssue"]


class NonIdempotentIssue(MemoryStore):
    """Mints a fresh issuance on every call — breaks S1 (idempotent issue)."""

    def issue(self, **kwargs: object) -> Issuance:
        kwargs["binding_hash"] = f"{kwargs['binding_hash']}-{uuid.uuid4().hex[:8]}"
        return super().issue(**kwargs)  # type: ignore[arg-type]


class GappedLedger(MemoryStore):
    """Hides the first ledger row — breaks S4 (gapless ledger)."""

    def read_ledger(self, since_seq: int = 0) -> tuple[LedgerRow, ...]:
        return super().read_ledger(since_seq)[1:]


class LooseConsume(MemoryStore):
    """Reports success without recording the consume — breaks S3 (single-use)."""

    def consume(self, issuance_id: str, *, now: int) -> ConsumeResult:
        result = super().consume(issuance_id, now=now)
        if result.status != "consumed" or result.issuance is None:
            return result
        # Undo the consumption so a replay succeeds.
        self._issuances[issuance_id] = result.issuance.__class__(
            **{**result.issuance.__dict__, "consumed_at": None, "status": "live"}
        )
        return ConsumeResult(status="consumed", issuance=result.issuance)


class AmoebaStore(MemoryStore):
    """Claims durability it does not have — breaks the honest-capability rule."""

    def capabilities(self) -> CapabilityFlags:
        return CapabilityFlags(
            single_writer=True, durable=True, atomic_issue=True, cluster_safe=False
        )
