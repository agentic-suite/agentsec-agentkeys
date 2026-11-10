# Ledger design — every transition is evidence (M7)

**Status:** design of record for M7 · **Issue:** #89 (`7.D0`) · **Written before implementation.**
**Sources:** [PRD 15 §4–§5](../prd/15-data-model.md), [PRD 05 R6/E12](../prd/05-features.md),
[PRD 17 §9](../prd/17-scenarios.md), [store design](store.md), [revoke design](revoke.md).

**BLUF:** Every issuance, use, upgrade, rejection, evasion, revocation, expiry, and sink gap is an
**agentwatch-schema event** and an append-only row in a **hash-chained ledger**. The chain makes the
record tamper-evident: a rewritten, reordered, or deleted row fails `verify-log`, reported with the
first bad `seq` — detected, never skipped. `export --session/--reference` emits a deterministic,
secret-free JSONL timeline that joins to a session trace by `session_id`.

---

## 1. The chain

```
seq      1, 2, 3 …                     gapless, strictly increasing
prev_hash = hash(previous row)          genesis row uses GENESIS_PREV_HASH ("0"*64)
hash      = SHA-256(canonical(event) ‖ prev_hash)
```

`verify_chain(rows)` recomputes both links for every row and returns a `ChainReport`:
`intact`, `rows`, `first_bad_seq`, `gap_seqs`, `reason`, `duplicate_seqs`. Any mismatch is a
`TAMPER` (exit `3`) with the offending `seq` named.

## 2. The event set (`event_version = "1.0"`, additive only)

| Event | Fires when | Severity |
|---|---|---|
| `reference-resolved` | a reference resolved to a registered slot (no secret yet) | info |
| `issuance.created` | a bound token was minted | info |
| `use` | a bound token was consumed at egress | info |
| `exchange-rejected` | a replay/forward/stale/cross-bound attempt failed | warn |
| `step-up-requested` / `step-up-granted` / `step-up-denied` | approval lifecycle (M10) | info / info / warn |
| `evasion-detected` | a raw-credential read outside the broker (M9) | high |
| `revoked` | a revoke CAS committed | high |
| `expired` | a TTL elapsed (once, via the expiry CAS) | info |
| `sink-gap` | events could not be shipped to the agentwatch sink | warn |

Each event carries the common fields (`event_version`, `occurred_at`, `monotonic_ms`, `session_id`,
`agent_id`, `reference_id`, `issuance_id`, `binding_json`, `ttl_seconds`, `principal`, `reason`,
`severity`). The emitter refuses an unknown name or severity — an allow-list, not a convention.

## 3. Export and verify-log

- `export --session <id>` / `export --reference <id>`: deterministic JSONL, ordered by `seq`, one
  object per line: `{"seq", "event", "prev_hash", "hash"}`. Written `0600` when `--out` is used.
  No plaintext secret exists in the ledger, so the export is secret-free by construction and the
  test scans it anyway.
- `verify-log`: read-only; recomputes the chain; `OK` (0) intact, `TAMPER` (3) broken with
  `first_bad_seq`; never migrates, never repairs.

## 4. Correlation

`correlate(rows)` groups rows by `session_id` and exposes the join keys
(`session_id`, `agent_id`, `reference_id`, `issuance_id`) plus the ordered transition names, so an
audit can join the ledger to the session trace without a second store.

## 5. Sink adapter

The local ledger is authoritative. `SinkAdapter.emit(row)` appends locally first, then tries the
sink; a failing sink retains the unsent buffer and appends one `sink-gap` event naming the first
unsent `seq` and the failure class (never a payload). Nothing is lost and nothing is silently allowed.

## 6. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 7.1 | `tests/test_ledger_chain.py` | chain verifies; rewritten/reordered/deleted row detected with `first_bad_seq` |
| 7.2 | `tests/test_events.py` | one event per transition; `event_version`; unknown name refused |
| 7.3 | `tests/test_export.py` | deterministic ordered JSONL; `0600`; zero secrets |
| 7.4 | `tests/test_export.py` | `verify-log` exits 3 on tamper, 0 intact |
| 7.5 | `tests/test_correlation.py` | join keys and ordered transitions per session |
| 7.6 | `tests/test_sink.py` | sink offline → gap marker; local chain intact; buffer retained |

Findings land in [`codereview-log.md`](../wbs/v0.1.0/codereview-log.md) at `7.CR`.
