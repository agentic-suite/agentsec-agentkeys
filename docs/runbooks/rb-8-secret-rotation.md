# Secret rotation

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

Rotate a backend value without restarting the agent.

## Steps

1. Rotate the value at the IdP / backend.
2. Re-run `agentkeys scan` to confirm zero literal values.

## Verification

The next resolution uses the new value; the pre-rotation token dies within its TTL.

Verify with `agentkeys doctor` (and `agentkeys verify-log` for the chain).
