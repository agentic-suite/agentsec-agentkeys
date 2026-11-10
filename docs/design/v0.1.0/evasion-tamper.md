# Evasion & tamper design — catch the bypass, fail closed on tamper (M9)

**Status:** design of record for M9 · **Issue:** #112 (`9.D0`) · **Written before implementation.**
**Sources:** [PRD 06 §3–§4](../../prd/06-security-baseline.md), [PRD 05 R7/E10](../../prd/05-features.md),
[PRD 17 SC-14–SC-17/SC-41](../../prd/17-scenarios.md), [ledger design](ledger.md).

**BLUF:** A raw-credential read outside the broker is a **high-severity event**, attributed and
joined to the ledger. In `enforce` mode it is **blocked only where an enforcer composes**; where none
does, the attempt is recorded and the **gap is named** — never claimed as a block. Tampering with the
broker's config fails closed and emits a loud `tamper-detected`; probing unknown references is an
evasion-class signal.

---

## 1. Evasion paths and classes

| Class | Paths | Why |
|---|---|---|
| `dotenv` | `.env`, `*.env`, `*.env.*` | the classic env-resident secret |
| `cloud-credential` | `~/.aws/credentials`, `~/.config/gcloud/application_default_credentials.json`, `~/.azure/*` | cloud blast radius |
| `keychain` | `login.keychain*`, `*.keychain-db`, `~/.local/share/keyrings/*` | direct backend read |
| `ssh-key` | `id_rsa`, `id_ed25519`, `*.pem`, `*.key` | long-lived machine identity |
| `env-export` | a process reading `AGENTKEYS_*` / credential env outside the broker | env fallback attempt |

`classify_path(path)` returns a class or `None`; an unrelated path is not an evasion.

## 2. Monitor vs enforce

```python
detector = EvasionDetector(mode="monitor" | "enforce", enforcer=callable | None)
verdict  = detector.observe(AccessAttempt(path=..., principal=..., session_id=...))
```

- **monitor**: `detected=True`, `blocked=False`, high severity. Always safe: we cannot block, so we
  do not claim to.
- **enforce + enforcer**: the enforcer is asked; `True` → `blocked=True`, `False`/exception →
  `blocked=False` and `gap_named=True` with the reason naming the uncovered path.
- **enforce without an enforcer**: `gap_named=True`; never a fabricated block.

Every detected attempt is one `evasion-detected` event (severity `high`, `principal`, class/path in
`reason`, no secret material).

## 3. Tamper resistance (E10)

- **Config integrity** — `ConfigIntegrity.pin()` records `SHA-256(config bytes)` at session start.
  `verify()` reports `ok` / `mismatch` / `missing`; `TamperGuard.check()` on any non-ok verdict appends
  a `tamper-detected` event and raises `TamperError` — issuance stops, nothing is repaired silently.
- **Reference enumeration** — repeated unknown-reference probes are recorded in a sliding window;
  crossing the threshold (`3` by default) raises the evasion-class signal (`reason:
  reference-enumeration`). The probe still raises `UnknownReference`; the signal is additive.
- **Ledger tamper** — `verify-log` (M7) detects a rewritten/deleted row; a broken chain is `TAMPER`.
- **Broker unavailable** — the store is the truth, so a closed/corrupt store makes resolution raise
  and no credential is minted (fail closed, SC-41 fixture).

## 4. Honest gaps

`enforce` is only as good as the composed enforcer (agentkernel/agentseatbelt). v0.1.0 ships the
classifier, the event, the hook contract, and the gap naming; it does **not** ship an OS-level enforcer.
The design says that plainly rather than claiming blocks it cannot deliver.

## 5. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 9.1/9.2 | `tests/test_evasion_detect.py` | classes; high event with attribution; unrelated path ignored |
| 9.3 | `tests/test_evasion_enforce.py` | blocked where composed; gap named where not; `enforce` never fakes a block |
| 9.4 | `tests/test_tamper_config.py` | pin/verify; edit → fail closed + `tamper-detected` |
| 9.5/9.6 | `tests/test_tamper_broker.py` | enumeration signal; spoofed reference denied; closed store denies |

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `9.CR`.
