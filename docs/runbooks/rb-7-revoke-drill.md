# Quarterly revoke drill

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

Scheduled drill of the ≤1s kill.

## Steps

1. Run `python -m agentkeys.bench.killtime --iterations 100`.
2. Enter p50/p95/max and pass/fail **by hand** in the field-test report.

## Verification

`passed: true` with p95 and max ≤1s; the report verdict is hand-entered, never generated.

Verify with `agentkeys doctor` (and `agentkeys verify-log` for the chain).
