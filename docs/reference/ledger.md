# Ledger reference — events, export, verify-log

> **Status: implemented (M7).** Design: [ledger design](../design/v0.1.0/ledger.md).

Every lifecycle transition is an agentwatch-schema event (`event_version = "1.0"`) in an append-only,
hash-chained ledger. Event names are stable within v0.x and additive only.

| Event | Severity | Fires when |
|---|---|---|
| `reference-resolved` | info | a reference resolved to a registered slot |
| `issuance.created` | info | a bound token was minted |
| `use` | info | a bound token was consumed at egress |
| `exchange-rejected` | warn | a replay/forward/stale/cross-bound attempt failed |
| `step-up-requested` / `step-up-granted` | info | an approval was asked for / granted |
| `step-up-denied` | warn | no approval, timeout, or a malformed decision |
| `evasion-detected` | high | a raw-credential read outside the broker, or reference enumeration |
| `tamper-detected` | high | config integrity failed |
| `revoked` | high | a revoke CAS committed |
| `expired` | info | a TTL elapsed (exactly once) |
| `sink-gap` | warn | the agentwatch sink was unavailable (named gap) |

Chain: `seq` is gapless from 1; `prev_hash` is the previous row's `hash` (all-zero genesis); `hash =
SHA-256(canonical(event) ‖ prev_hash)`.

## `agentkeys export`

`--session ID` or `--reference ID` (exactly one), `--out PATH`, `--json`, `--config PATH`.

Without `--out`, ordered JSONL is printed (`{"seq","event","prev_hash","hash"}` per line). With `--out`,
the file is written `0600`. The ledger stores no plaintext secret, so the export is secret-free by
construction (SC-31).

## `agentkeys verify-log`

Recomputes every link; read-only, never repairs. `0` intact · `3` tamper (the payload names
`first_bad_seq`) · `2` config/store failure. A rewritten, reordered, or deleted row is detected, never
skipped (SC-30).

## Correlation

`agentkeys.correlation.correlate(rows)` groups rows per `session_id` and exposes `agent_id`,
`reference_id`, and `issuance_id` join keys plus the ordered transitions — an audit joins the ledger to a
session trace without a second store.
