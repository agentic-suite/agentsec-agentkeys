# Store reference — the BrokerStore contract (v0.1.0)

**Status:** implemented in M1 · **Owner module:** `src/agentkeys/store/` ·
**Design:** [store design](../design/v0.1.0/store.md) · **Issue:** WBS 1.D.

**BLUF:** The store is the broker's only path to persisted state. Everything the broker decides — an
issuance, a consumption, a revocation, a lifecycle event — is a row written through `BrokerStore`. The
contract is six semantics, four capability flags, and two drivers that pass the same conformance suite.

## The one-state-path rule

- Only `BrokerStore` reads or writes state. Backends (M3) resolve secrets and never write; the ledger is
  appended through `append_event`/`issue`/`cas_revoke`, never by a driver side effect.
- A driver is admitted only if it exposes the full surface ([`loader.admit_driver`](../../src/agentkeys/store/loader.py));
  a missing capability is a hard refusal — there is no degraded mode.

## Semantics (normative)

| # | Semantic | What it guarantees |
|---|---|---|
| S1 | **Idempotent issue** | At most one issuance per `(binding_hash, window)`; a retry returns the same record and appends no event. |
| S2 | **CAS revoke** | `revoke_epoch` advances by exactly one, only for the winner; a loser gets the winner's revocation with `winner: false`. Revocation is never policy-gated. |
| S3 | **Single-use consume** | `consumed_at` is set once. Outcomes are typed: `consumed`, `already_consumed`, `expired`, `unknown`. |
| S4 | **Gapless hash-chained ledger** | `seq` is contiguous from 1; `hash = H(canonical(event) ‖ prev_hash)` with an all-zero genesis anchor; rows are never updated or deleted. |
| S5 | **Exactly-once recovery** | A crash mid-issue leaves either the whole issuance or none of it. A retry then succeeds exactly once. |
| S6 | **Durable-commit-before-ack** | `issue` returns only after the commit is durable (SQLite `synchronous=FULL`). |

## Capability flags

| Flag | Meaning | Required by |
|---|---|---|
| `single_writer` | One broker process owns the store. | the broker core |
| `durable` | Committed writes survive a crash and a new process. | anything that must not lose a decision |
| `atomic_issue` | Binding + issuance + ledger row commit in one transaction. | the resolution core (M2) |
| `cluster_safe` | Safe under multiple writers / a cluster. | server/HA mode (v0.2.0) |

`require_capabilities(flags, needed)` raises `CapabilityError` naming the missing flag. Callers that need
durability must pass it explicitly — a driver that cannot deliver is refused, not tolerated.

## Drivers

| Name | Flags | Notes |
|---|---|---|
| `sqlite` | `single_writer`, `durable`, `atomic_issue` | Single file, WAL, `synchronous=FULL`, dir `0700`, store `0600`. `:memory:` reports `durable=False`. |
| `memory` | `single_writer`, `atomic_issue` | In-process, lock-protected, ephemeral: tests and embedded use. |

`load_driver("sqlite", path=…)` resolves either driver through the `agentkeys.store` entry-point group;
an unknown name is a usage error (exit `1`), a missing capability is a denial (exit `2`).

## Error mapping

| Store error | Meaning | CLI exit |
|---|---|---|
| `DriverNotFound` | Unknown driver name; the known names are listed. | `1` |
| `DriverError` | Unimportable or unconformant driver. | `1` |
| `CapabilityError` | The driver cannot deliver a required capability. | `2` |
| `StoreBusyError` | Another writer holds the store. | `2` |
| `StoreVersionError` | The store is newer than this binary, or corrupt. | `3` (refuse loudly) |
| `StoreError` | Any other fail-closed store failure. | `2` |

## Schema

Schema version **1** (see [`schema.py`](../../src/agentkeys/store/schema.py) for the DDL). Tables:
`references`, `sessions`, `bindings`, `issuances`, `revocations`, `backends`, `redaction_receipts`,
`ledger`. **No table holds secret material** — `issuances.secret_hash` is a hash (PRD 15 §6). Migrations
are forward-only; a newer store refuses loudly and is never modified.

## Honest limits

- M1 writes `references`, `sessions`, `bindings`, `issuances`, `revocations`, `ledger`, and receipts. The
  `backends` registry table exists in the schema but is populated from M3.
- Broad revocation scopes (`--agent`, `--all`) are recorded in M1 but fan out to per-session CAS in M6.
- Full behavioural conformance gating for *third-party* drivers arrives with the conformance kit (M11);
  the M1 loader gates shape + capability declaration and says so.
- Retention/pruning is not implemented (M7 owns the lifecycle policy).

## Related

- [Store design (decisions + rationale)](../design/v0.1.0/store.md)
- [Driver-author conformance guide](store-conformance.md)
- Contracts behind the records: [PRD 15 — Data model](../prd/15-data-model.md)