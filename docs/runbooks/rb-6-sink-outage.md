# agentwatch sink outage

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

Events are not shipping; a `sink-gap` event appears in the ledger.

## Steps

1. Confirm the local ledger is authoritative and intact.
2. Restore sink connectivity; the buffered events flush.

## Verification

`sink-gap` markers are named, `verify-log` exits 0, and no event was lost.

Verify with `agentkeys doctor` (and `agentkeys verify-log` for the chain).
