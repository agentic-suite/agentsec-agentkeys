# Backends reference — drivers, failure semantics, redaction (v0.1.0)

**Status:** implemented in M3 · **Owner modules:** `src/agentkeys/backends/`, `src/agentkeys/redact.py` ·
**Design:** [backends design](../design/v0.1.0/backends.md) · **Issue:** WBS 3.D.

**BLUF:** One `Backend` contract, two drivers, one fail-closed engine, one redactor. A plaintext secret is
only ever a `SecretValue`, which refuses to be logged, formatted, or serialised; `resolve` never falls back.

## The contract

`resolve(path) -> SecretValue` · `list() -> tuple[str, ...]` (paths only) · `health() -> BackendHealth`
(states: `healthy`, `locked`, `absent`, `ambiguous`, `unconfigured`) · `capabilities() ->
BackendCapabilities(read_only, interactive_unlock, file_backed, conformance_version)`.

`SecretValue` is opaque: `reveal()` is the only accessor; `repr`, `str`, `format`, and comparisons to text
never expose it. Introducing a value into a log line requires calling `reveal()` explicitly.

## Drivers

| Driver | Kind | Capabilities | Behaviour |
|---|---|---|---|
| keychain | `keychain` | `interactive_unlock=True` | macOS `security find-generic-password -w -s <service> -a <path>`; Linux `secret-tool lookup service <service> account <path>`. Unlock-per-resolve, no caching, no plaintext written to disk. `list()` reports the enumeration limitation honestly. |
| file | `file` | `file_backed=True`, `read_only=True` | A `0600` credential file: a JSON object or `NAME=value` lines. Permissions are checked at open **and** at every resolve, so a widened mode is refused immediately. Re-read on every resolve, so rotation lands without a restart. |

Both drivers pass the same [conformance suite](backends-conformance.md); a broken driver fails it.

## Failure semantics (fail closed)

| Backend failure | Engine result | Effect on issuance |
|---|---|---|
| keychain locked / unlock in progress | `Denial("backend-locked")` | deny or pending — never allow |
| slot absent | `Denial("backend-absent")` | deny |
| more than one candidate | `Denial("backend-ambiguous")` | deny (never first-match-wins) |
| tool missing / service down | `Denial("backend-unavailable")` | deny |
| material readable beyond its owner | `Denial("backend-permission")` | deny |
| unregistered backend id | `Denial("unknown-backend")` | deny |

A denial names the backend and the slot and never carries a value. There is no fallback to an environment
variable, a config value, or a cached plaintext; the fault matrix is **100% deny-or-pending** (exercised by
`tests/test_failclosed_matrix.py`).

`doctor` renders `FailClosedEngine.health_report()` so the effective backend set and its health are explained.

## Redaction

`redact(text, field="text") -> Redaction(text, receipts)` masks before anything is stored, rendered, or
exported. Masked spans keep a four-character tail (`***…7f2a`) for correlation. Classes: `api-key`,
`bearer`, `jwt`, `private-key`, `connection-string`, `env-assignment`. One receipt per masked field with a
count; receipts persist through the store (`redaction_receipts`). `looks_like_secret` and the pattern set are
the single source shared with the M0 config validator and the M2 contract guards.

## Honest limits

- Only the keychain and file drivers exist at v0.1.0; enterprise/cloud backends are R10 (v0.1.x).
- Keychain enumeration is not portable and is not implemented; references are how you name slots.
- Behavioural conformance gating of third-party backends at install time is M11.
- The redactor is pattern-based (known shapes); it is not a general entropy classifier. M9 adds evasion
  detection for shapes it cannot see, and reports the gap rather than claiming coverage.
