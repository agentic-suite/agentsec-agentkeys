# Contracts reference — `akref/1.0` and `issuance/1.0` (v0.1.0)

**Status:** implemented in M2 · **Owner modules:** `src/agentkeys/contracts/`, `src/agentkeys/core/` ·
**Design:** [contracts design](../design/v0.1.0/contracts.md) · **Issue:** WBS 2.D.

**BLUF:** Two versioned documents, both safe to log. The reference names a backend slot; the issuance
records a bound, single-use grant. **Neither carries a secret**: the token exists only transiently at
egress, and the store holds `secret_hash` alone.

## `akref/1.0` — the reference

| Field | Required | Notes |
|---|---|---|
| `akref` | ✓ | Contract version, `"1.0"` |
| `reference_id` | ✓ | Stable opaque id (`ref_…`) |
| `backend` | ✓ | Registered backend id |
| `path` | ✓ | Backend-native **slot name** (never a value) |
| `class` | ✓ | `public` \| `dev` \| `staging` \| `prod` |
| `scope_hint` | – | Advisory; never widens a binding |
| `label` | – | Human label |

Refused at construction: a missing/empty required field, an unknown `class`, and any value that matches a
known credential shape (`sk-…`, `ghp_…`, `AKIA…`, PEM headers, JWTs) in `path`, `reference_id`,
`scope_hint`, or `label`. Unknown fields are ignored (additive, E11).

**Key grammar** (registry keys): `akref:<backend>/<path>`, where `<backend>` is `[a-z][a-z0-9_-]*` and
`<path>` is a relative path with no `..` segment. Malformed keys are refused with the failing part named;
well-formed-but-unknown keys are an `UnknownReference`.

## `issuance/1.0` — the issuance

| Field | Required | Notes |
|---|---|---|
| `issuance` | ✓ | Contract version, `"1.0"` |
| `issuance_id` | ✓ | Stable opaque id (`iss_…`) |
| `reference_id` | ✓ | The reference being resolved |
| `session_id` | ✓ | Session binding |
| `agent_id` | ✓ | Agent identity |
| `binding` | ✓ | `{ "audience", "tool" }` |
| `class` | ✓ | Class at mint |
| `ttl` | ✓ | Seconds, within the class window |
| `issued_at` / `expires_at` | ✓ | `expires_at == issued_at + ttl` |
| `provenance` | – | `{ "decided_by", "decision" }` for a higher-class mint |

**There is no `secret_hash` field** on the wire, and no field that could hold a token: the document is
metadata only. A secret-shaped value in any string field (including `provenance` values) is refused.

## Resolution

`ResolutionCore.resolve(reference_id, audience, tool, session_id)` runs the ordered pipeline: session
exists and is unrevoked → reference is registered → the binding is allowlisted → (class gate: M10) → the
idempotency window `now // window_seconds` → mint a 128-bit token, store only its SHA-256, and append the
ledger row in one transaction.

- **Idempotent (E1):** a retry in the same `(binding_hash, window)` returns the same issuance; nothing new
  is minted and no event is appended.
- **Transient token:** the plaintext is returned once, cached in-process only while live, and redacted in
  `repr`. Across processes a retry returns the issuance with `token=None` — nothing durable held it.
- **Single-use (E3):** `use(issuance_id, token)` compares hashes in constant time, then CAS-consumes.
  Outcomes are typed: `consumed`, `already_consumed`, `expired`, `rejected` (wrong token), `unknown`.

## Denials

| Failure | Result |
|---|---|
| unknown / revoked session | `ResolutionDenied("unknown-session" / "session-revoked")` |
| unregistered reference | `UnknownReference` |
| binding not allowlisted | `ResolutionDenied("binding-not-allowed")` |
| TTL outside the class window | `IssuanceError` (never clamped) |
| wrong token | `UseResult("rejected")` |

CLI mapping: a denial is exit `2`; a usage error is exit `1`.

## Embedder surface

`agentkeys.sdk.Broker` exposes `register_reference`, `list_references`, `resolve`, `use`, `get_issuance`,
`revoke`. **No `get_secret()` exists** — a test asserts no public name contains `secret` or `plaintext`.

## Honest limits

- Step-up approval (class gate) is M10; M2 denies the class only if a deployment marks it
  approval-required.
- Egress delivery of the token is M4/M5. M2 mints and consumes; it does not inject.
- Enumeration-probe detection over lookups is M9.

## Related

- [Contracts design](../design/v0.1.0/contracts.md) · [Store reference](store.md)
- [PRD 15 — Data model](../prd/15-data-model.md) · [PRD 18 — Issuance integrity](../prd/18-issuance-integrity.md)