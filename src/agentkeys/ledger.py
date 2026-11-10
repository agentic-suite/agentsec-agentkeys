"""The hash-chained ledger verifier (M7, WBS 7.1/7.4; R6, E12).

`verify_chain` recomputes every link and reports the first bad `seq`. It never repairs, never
skips: a rewritten, reordered, or deleted row is a `TAMPER`, not a warning.
"""

from __future__ import annotations

from dataclasses import dataclass

from agentkeys.store.contract import GENESIS_PREV_HASH, LedgerRow, compute_hash

__all__ = ["ChainReport", "verify_chain"]


@dataclass(frozen=True)
class ChainReport:
    """The integrity verdict for a ledger read."""

    intact: bool
    rows: int
    first_bad_seq: int | None = None
    gap_seqs: tuple[int, ...] = ()
    duplicate_seqs: tuple[int, ...] = ()
    reason: str | None = None


def verify_chain(rows: tuple[LedgerRow, ...]) -> ChainReport:
    """Recompute the chain; any mismatch is reported at the offending `seq`."""
    if not rows:
        return ChainReport(intact=True, rows=0)

    seen: set[int] = set()
    duplicates: list[int] = []
    for row in rows:
        if row.seq in seen:
            duplicates.append(row.seq)
        seen.add(row.seq)
    if duplicates:
        first = min(duplicates)
        return ChainReport(
            intact=False,
            rows=len(rows),
            first_bad_seq=first,
            duplicate_seqs=tuple(sorted(set(duplicates))),
            reason=f"duplicate seq: {first}",
        )

    gaps: list[int] = []
    previous_hash = GENESIS_PREV_HASH
    expected_seq = 1
    for row in rows:
        if row.seq != expected_seq:
            gaps.append(expected_seq)
            return ChainReport(
                intact=False,
                rows=len(rows),
                first_bad_seq=row.seq,
                gap_seqs=tuple(gaps),
                reason=f"gap: expected seq {expected_seq}, found {row.seq}",
            )
        if row.prev_hash != previous_hash:
            return ChainReport(
                intact=False,
                rows=len(rows),
                first_bad_seq=row.seq,
                reason=f"prev_hash mismatch at seq {row.seq}",
            )
        expected_hash = compute_hash(row.event, row.prev_hash)
        if row.hash != expected_hash:
            return ChainReport(
                intact=False,
                rows=len(rows),
                first_bad_seq=row.seq,
                reason=f"hash mismatch at seq {row.seq}",
            )
        previous_hash = row.hash
        expected_seq += 1
    return ChainReport(intact=True, rows=len(rows))
