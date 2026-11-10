# Upgrade day

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

A new binary opens an older store, or refuses a newer one.

## Steps

1. Back up first: `agentkeys backup --out <file>`.
2. Run `agentkeys doctor` before serving traffic.

## Verification

Forward migration succeeds; a downgrade refuses loudly (`schema_version ... newer than supported`) and writes nothing. Verify with `agentkeys verify-log` and `agentkeys doctor`.
