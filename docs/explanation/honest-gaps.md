# Honest gaps — what v0.1.0 does not do

> **Status: documented (M13).** Claims follow the PRD 20 vocabulary; nothing here is field-tested until
> the hand-maintained M14 report says so.

## Not implemented in v0.1.0

| Area | Gap | Status |
|---|---|---|
| `agentkeys init`, `context-dump`, `scan-usable` | not yet implemented (quickstart writes the config directly) | not yet |
| `migrate --backend keychain` | only the `0600` file backend is implemented; keychain migration refuses honestly | not yet |
| `scan --ci` | scheduled for v0.1.x; refuses as not-yet | not yet |
| OS-level evasion enforcer | `enforce` blocks only where an enforcer (agentkernel/agentseatbelt) composes; otherwise a named gap | limitation |
| RFC 9449 DPoP | deferred to v0.3.0 (R14) | not supported |
| Enterprise backends (Vault/1Password/cloud SM) | v0.1.x (R10); an unknown driver refuses | not supported |
| Signed release / SLSA / Sigstore attestation | M15 owns signing and the security audit; M11 ships the in-repo floor only | not claimed |
| Live harness field runs | M14 field test; tests prove the wiring, not a customer environment | not field-tested |
| Cloud/HA server mode | R11 (v0.1.x) | not supported |

## What v0.1.0 does claim (with evidence)

- References in context, secrets only at egress — tested (R1/R2, `tests/test_reference_contract.py`, injectors).
- Audience/tool/session bindings and single use — tested (`tests/test_binding_*`, `test_resolution.py`).
- Revoke ≤1s, replay-verified — tested (`tests/test_revoke_killtime.py`); field re-run at M14.
- Hash-chained ledger, export, verify-log — tested (`tests/test_ledger_chain.py`, `test_export.py`).
- Scan/migrate with 100% recall on the seeded corpus and zero printed values — tested (SC-51 fixture).
- Step-up approval with recorded provenance — tested (`tests/test_stepup_*`).

## Field-test labels

A scenario is *field-tested* only when a human records its verdict in
`docs/field-test/<version>/FIELD_TEST_REPORT.md`. No automation writes that report.
