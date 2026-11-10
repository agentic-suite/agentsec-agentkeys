# Security surface — invariant and detection

> **Status: implemented (M3–M9).**

- **Never-in-context (R1):** agents hold references only; secret resolution happens at egress and the
  plaintext token is never persisted. Context-dump attack pack: [attack packs](../design/v0.1.0/conformance-supplychain.md).
- **Fail closed (E4):** locked/absent/ambiguous backends deny issuance; a corrupt or unavailable store
  denies; the broker never falls back to an env value or a static secret.
- **Evasion detection (R7):** `.env`, cloud credential files, keychain, ssh-key, and env-export reads are
  classified and recorded as high-severity `evasion-detected` events. Enforce mode blocks only where an
  enforcer composes; otherwise the gap is **named**.
- **Tamper (E10):** config integrity is pinned and verified (`tamper-detected`), the ledger chain is
  verified (`verify-log` exit `3`), stale serve locks are reported, and unknown-reference enumeration raises
  an evasion-class signal.
- **Redaction (E5):** [the redactor](contracts.md) masks before persistence; receipts annotate masked fields;
  the [evidence scanner](../design/v0.1.0/conformance-supplychain.md) proves zero secret material.

Honest limits: [honest gaps](../explanation/honest-gaps.md).
