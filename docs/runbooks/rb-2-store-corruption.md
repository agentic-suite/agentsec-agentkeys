# Store corruption or a broken chain

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

`agentkeys verify-log` exits `3` or `doctor` reports `chain` broken.

## Steps

1. Stop the broker (`serve` exits on SIGTERM).
2. Restore the last verified backup: `agentkeys restore --from <backup>`.

## Verification

`agentkeys verify-log` exits 0 on the restored store and `agentkeys doctor` is green. Restore refuses a backup whose chain is broken.
