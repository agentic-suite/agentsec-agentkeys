# Suspected exfiltration

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

High-severity `evasion-detected` events or an unexpected `reference-enumeration` signal.

## Steps

1. `agentkeys revoke --all` (explicit, unconditional).
2. `agentkeys export --session <id>` and read the timeline (secret-free).
3. Rotate the backend secret with its IdP.

## Verification

`revoked` events for every session; `agentkeys replay --last` exits `4`; evidence scanner finds 0 secrets in the export.
