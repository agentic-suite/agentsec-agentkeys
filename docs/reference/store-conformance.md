# Store conformance suite — the contract's executable form (v0.1.0)

**Status:** implemented in M1 · **Suite:** [`tests/store_conformance.py`](../../tests/store_conformance.py) ·
**Design:** [store design](../design/v0.1.0/store.md) §9.

**BLUF:** A store driver is only trustworthy if it passes the same suite the reference driver passes. The
suite is deliberately strict — four deliberately broken drivers are tested to **fail** it, so a green run
means something.

## Running it

```python
from tests.store_conformance import run_conformance
from agentkeys.store.sqlite import SqliteStore

findings = run_conformance(lambda key: SqliteStore(f"/tmp/{key}.db"))
assert findings == [], findings
```

The factory receives a **namespace key** and must return a store isolated to that key (a distinct file, or
a fresh in-memory store). Every check runs against its own key, so a file-backed driver cannot see another
check's writes.

## What it asserts

| Check | Semantic |
|---|---|
| `capabilities_are_declared` | `capabilities()` returns flags; `atomic_issue` is True. |
| `capability_refusal_is_enforced` | `require_capabilities` refuses a missing flag. |
| `references_are_idempotent` | Re-creating a reference returns it; a conflicting one is refused. |
| `issue_is_idempotent_per_binding_and_window` | S1: a retry returns the same issuance, appends no event, and does not double-count. |
| `consume_is_single_use` | S3: `consumed` → `already_consumed`; unknown ids are `unknown`. |
| `expiry_is_enforced` | An expired issuance cannot be consumed and is not marked consumed. |
| `live_reads_exclude_consumed_and_expired` | `list_live` returns only genuinely live issuances. |
| `revoke_has_one_winner_and_a_monotonic_epoch` | S2: one winner, epoch +1, loser gets the winner's revocation, unknown target errors. |
| `ledger_is_gapless_and_hash_chained` | S4: contiguous seq, correct genesis, recomputable chain, duplicate ids refused, scoped export. |
| `receipts_round_trip` | A redaction receipt is stored and read back. |
| `declared_durability_is_honest` | A driver that declares `durable` must keep data across instances. |

## Proving the suite can fail

`tests/conformance_fakes.py` provides four broken drivers and `tests/test_store_conformance.py` asserts
each one **fails** the suite with the expected finding:

| Fake | Broken rule |
|---|---|
| `NonIdempotentIssue` | mints a fresh issuance on every call (breaks S1) |
| `GappedLedger` | hides a ledger row, so `seq` is not contiguous (breaks S4) |
| `LooseConsume` | reports success without recording the consume (breaks S3) |
| `AmoebaStore` | declares `durable=True` while losing data (breaks honest capabilities) |

## Writing a new driver

1. Implement every method in `agentkeys.store.contract.BrokerStore` and return `CapabilityFlags` from
   `capabilities()` — declared flags are a contract, not a hint.
2. Register it in the `agentkeys.store` entry-point group
   (`[project.entry-points."agentkeys.store"] name = "module:Class"`).
3. Run `run_conformance` in your own test suite; it must return no findings.
4. Keep the one-state-path rule: no secret material in any column (only `secret_hash`), and never write the
   store outside the contract.

## Honest limits

- The suite exercises the contract's *shape and semantics*; it does not test crash durability of a
  third-party driver. In M1 only the SQLite driver is crash-tested
  ([`tests/test_store_recovery.py`](../../tests/test_store_recovery.py), S5).
- Behavioural conformance gating of third-party drivers at install time arrives with the conformance kit
  (M11, E13).
