# Evasion & tamper reference

> **Status: implemented (M9), enforcer hook shipped without an OS enforcer.** Design:
> [evasion/tamper design](../design/v0.1.0/evasion-tamper.md).

## Evasion detection (R7)

`agentkeys.evasion.classify_path` maps a raw read to a class: `dotenv`, `cloud-credential`, `keychain`,
`ssh-key`, `env-export`, or `None` (not an evasion).

- **monitor** — the attempt is detected and recorded as a high-severity `evasion-detected` event; no block
  is claimed.
- **enforce** — the attempt is blocked **only** when a composed enforcer returns `True`. A declining,
  failing, or absent enforcer produces `blocked=False`, `gap_named=True`, and a reason naming the gap.
  agentkeys never claims a block it did not perform.

Events carry the class and path, `principal`, and `session_id` — never a secret.

## Tamper resistance (E10)

- `ConfigIntegrity(path).pin()` records the SHA-256 of the config at session start; `verify()` reports
  `ok`, `config-tampered`, `config-missing`, or `config-not-pinned`.
- `TamperGuard(store, integrity).check()` appends `tamper-detected` (high) and raises `TamperError` on any
  non-ok verdict — issuance stops; nothing is repaired into an allow.
- `EnumerationSignal(threshold=3, window_seconds=60)` counts unknown-reference probes; crossing the
  threshold appends `evasion-detected` with reason `reference-enumeration`.
- A closed or corrupt store denies resolution (`StoreError`); the ledger verifier (`verify-log`) reports
  tamper as exit `3`.

## Honest gap

v0.1.0 ships the classifier, event, hook contract, and gap naming; it does **not** ship an OS-level
enforcer. Enforce mode is only as strong as the enforcer you compose (SC-17 WARN where none is present).
