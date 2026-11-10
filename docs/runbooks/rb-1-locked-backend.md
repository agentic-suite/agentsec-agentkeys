# Locked backend (keychain)

> **Status: documented (M13).** Verification steps use commands implemented in v0.1.0.

## Symptom

Issuance denied with `backend locked`; `doctor` shows the backend unhealthy.

## Steps

1. Unlock the OS keychain / Secret Service.
2. Re-run `agentkeys doctor`; the `backends` check must be green.
3. Retry the call.

## Verification

`agentkeys doctor` exits 0 and a resolve succeeds. **Never** bridge a locked backend with a literal secret or an env fallback.
