# PRD 15 — Data Model

**BLUF:** This is the data design of record for agentkeys v0.1.0: the **entities** (Reference, Issuance,
Binding, Session, Revocation, LifecycleEvent, Backend, RedactionReceipt), the two versioned wire contracts
(`akref/1.0` reference, `issuance/1.0` issuance), the **agentwatch lifecycle event set**, the **SQLite schema
outline** with the hash-chain columns, the **integrity rules**, the **config keys**, and the
**data-lifecycle/retention** semantics. The one invariant that shapes every table: **no field ever stores
secret material** — only references, hashes, bindings, times, and reasons. Everything here is *documented*
design; none of it is *field-tested* yet, and the v0.1.0 code has not started.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Entities and fields

Times are UTC ISO-8601. **No column below holds a secret value**; where a value would be sensitive, only a
hash or a class label is stored (E5). A **Session** has many **Issuances**; each Issuance names one
**Reference** and one **Binding**; a **Revocation** closes a Session's Issuances at the store; every state
change appends a **LifecycleEvent**; **RedactionReceipts** annotate any event/issuance with a masked field.

| Entity | Key | Fields |
|---|---|---|
| **Reference** | `reference_id` | `akref_version`, `backend`, `path`, `class`, `scope_hint`, `label`, `created_at`, `created_by` |
| **Issuance** | `issuance_id` | `reference_id`, `session_id`, `agent_id`, `audience`, `tool`, `class`, `ttl_seconds`, `issued_at`, `expires_at`, `secret_hash`, `single_use`, `consumed_at`, `provenance_json`, `status` |
| **Binding** | `binding_hash` (unique) | `reference_id`, `audience`, `tool`, `session_id`, `first_seen_at`, `issuance_count` |
| **Session** | `session_id` | `agent_id`, `harness`, `started_at`, `ended_at`, `status`, `revoke_epoch`, `principal` |
| **Revocation** | `revocation_id` | `scope`, `target_id`, `requested_by`, `requested_at`, `effective_at`, `reason`, `epoch_after` |
| **LifecycleEvent** | `event_id`; `seq` | `event_version`, `event_name`, `occurred_at`, `monotonic_ms`, `session_id`, `agent_id`, `reference_id`, `issuance_id`, `binding_json`, `ttl_seconds`, `principal`, `reason`, `severity`, `prev_hash`, `hash` |
| **Backend** | `backend_id` | `kind`, `display_name`, `capability_flags`, `health`, `conformance_version`, `added_at` |
| **RedactionReceipt** | `receipt_id` | `subject_id`, `field`, `class`, `count`, `redactor_version`, `created_at` |

**Field semantics that carry the invariants (not just types):**

- `Reference.path` names a backend slot; it is **not**, and must never be, the secret.
- `Reference.class` ∈ `public` | `dev` | `staging` | `prod` — drives TTL bounds (§7) and step-up gating.
- `Issuance.secret_hash` hashes the 128-bit single-use secret; the secret is **never** stored (E3).
- `Issuance.consumed_at` is set once, by CAS, on first use → single-use; `status` ∈ `issued` | `consumed` | `expired` | `revoked` | `rejected`.
- `Binding.binding_hash` = `H(reference_id ‖ audience ‖ tool ‖ session_id)`; uniqueness backs exactly-once issuance (§6).
- `Session.revoke_epoch` is the monotonic kill token, incremented by CAS on revoke (R4).
- `Revocation.effective_at` is measured against the **≤1s** target; `requested_by` gives attribution.
- `LifecycleEvent.seq` / `prev_hash` / `hash` form the tamper-evident chain (§5).
- `Backend.capability_flags` ∈ `single_writer`, `durable`, `atomic_issue`, `cluster_safe`; a failing capability refuses to load (E2, E9).
- `RedactionReceipt` records `field`, `class`, `count` for every masked secret-shaped value (E5).

> **Implemented (M2, 2026-11-09).** The reference and issuance contracts below are built in
> `src/agentkeys/contracts/` with the resolution pipeline in `src/agentkeys/core/resolution.py`; see the
> [contracts reference](../reference/contracts.md). `secret_hash` (see §5) is the only secret-adjacent
> column and is never on the wire.

## 2. The reference contract (`akref/1.0`)

A **versioned JSON** document. It is **safe to print, serialize, and log**: no secret bytes, resolvable only
by the broker, scoped by backend policy. Unknown fields are ignored (additive compatibility, E11).

| Field | Required | Type | Meaning |
|---|---|---|---|
| `akref` | ✔ | string | Contract version, `"1.0"` |
| `reference_id` | ✔ | string | Stable opaque id |
| `backend` | ✔ | string | Registered backend id |
| `path` | ✔ | string | Backend-native locator (**not** a secret) |
| `class` | ✔ | string | `public` \| `dev` \| `staging` \| `prod` |
| `scope_hint` | — | string | Advisory scope; never widens a binding |
| `label` | — | string | Human label |

```json
{
  "akref": "1.0",
  "reference_id": "ref_01HX8FAKE000000000000000000",
  "backend": "keychain",
  "path": "agentkeys/dev/example-api-token",
  "class": "dev",
  "scope_hint": "repo:read",
  "label": "Example API token (dev) — FAKE reference, no secret"
}
```

> The `path` **names a slot** in a backend; it is not, and must never be, the secret. A context-dump that
> captures this document yields nothing usable (R1, [PRD 06](06-security-baseline.md) §5).

## 3. The issuance contract (`issuance/1.0`)

The record the broker mints and records. **The token value itself is never stored or returned as a field
here** — only the hashed single-use secret (`secret_hash`, §5) and the binding. The plaintext credential
exists only transiently at egress ([PRD 02](02-architecture.md) §2).

| Field | Required | Type | Meaning |
|---|---|---|---|
| `issuance` | ✔ | string | Contract version, `"1.0"` |
| `issuance_id` | ✔ | string | Stable opaque id |
| `reference_id` | ✔ | string | Reference being resolved |
| `session_id` | ✔ | string | Session binding |
| `agent_id` | ✔ | string | Agent identity |
| `binding` | ✔ | object | `{ "audience", "tool" }` |
| `class` | ✔ | string | Class at mint |
| `ttl` | ✔ | integer | Seconds; within class floor/ceiling (§7) |
| `issued_at` | ✔ | timestamp | UTC |
| `expires_at` | ✔ | timestamp | UTC |
| `provenance` | — | object | `{ "decided_by", "decision" }` (step-up) |

```json
{
  "issuance": "1.0",
  "issuance_id": "iss_01HX8FAKE111111111111111111",
  "reference_id": "ref_01HX8FAKE000000000000000000",
  "session_id": "sess_01HX8FAKE222222222222222222",
  "agent_id": "claude-code:local",
  "binding": { "audience": "https://mcp.example.invalid", "tool": "issues.create" },
  "class": "dev",
  "ttl": 300,
  "issued_at": "2026-11-08T12:00:00Z",
  "expires_at": "2026-11-08T12:05:00Z",
  "provenance": { "decided_by": "agentpolicy", "decision": "allow" }
}
```

No field in this document is a credential. `secret_hash` lives only in the store (§5), never on the wire.

## 4. The agentwatch lifecycle event set

Every transition emits one event in the agentwatch schema. Event names are **stable within v0.x and additive
only** (E11). Common fields: `event_version`, `session_id`, `agent_id`, `reference_id`, `binding` (audience
+ tool), `ttl`, `principal`, `reason`.

| Event | Fires when | Salient fields | Severity |
|---|---|---|---|
| `reference-resolved` | A reference resolved to a backend slot (no secret yet) | `reference_id`, `backend`, `class` | info |
| `issuance` | A mint was requested (pre-outcome) | `reference_id`, `binding`, `ttl`, `class` | info |
| `issued` | A bound token was minted | `issuance_id`, `binding`, `ttl`, `expires_at` | info |
| `use` | A bound token was consumed at egress | `issuance_id`, `binding`, `principal` | info |
| `exchange-rejected` | A replay/forward/stale/cross-bound attempt failed | `issuance_id`, `binding`, `reason` | warn |
| `step-up-requested` | A higher-class mint asked agentpolicy | `reference_id`, `class`, `principal` | info |
| `step-up-granted` | An approval returned `allow` | `issuance_id`, `class`, `principal` | info |
| `step-up-denied` | No approval / timeout / deny | `reference_id`, `class`, `reason` | warn |
| `evasion-detected` | A raw-credential read outside the broker | `reference_id`?, `reason`, `principal` | **high** |
| `revoked` | A revoke CAS committed | `scope`, `target_id`, `principal`, `effective_at` | **high** |
| `expired` | A TTL elapsed (fires once) | `issuance_id`, `ttl` | info |

| Field | Present on | Notes |
|---|---|---|
| `event_version` | all | Schema version (additive) |
| `session_id` | all | Trace join key |
| `agent_id` | all | |
| `reference_id` | most | Absent on session-/agent-level `revoked` |
| `binding` | issuance-lifecycle events | `{ audience, tool }` |
| `ttl` | issuance events | Seconds |
| `principal` | actor/operator events | Attribution |
| `reason` | refusals, denials, evasions | Redacted, free text |

## 5. Storage: SQLite schema outline

Reference driver is **SQLite (WAL)** exposed only through the **BrokerStore** contract with declared
capability flags (`single_writer`, `durable`, `atomic_issue`) — the core refuses a driver it cannot trust
(E2, F15). Only SQLite/memory are v0.1.0 drivers.

```sql
-- schema_version(version INTEGER NOT NULL)                 -- migrations (§5)
-- references(reference_id PK, akref_version, backend, path, class,
--            scope_hint, label, created_at, created_by)
--   index: references_backend_path (backend, path)
-- sessions(session_id PK, agent_id, harness, started_at, ended_at,
--          status, revoke_epoch INTEGER NOT NULL DEFAULT 0, principal)
--   index: sessions_agent (agent_id, status)
-- bindings(binding_hash PK, reference_id, audience, tool, session_id,
--          first_seen_at, issuance_count)
--   index: bindings_ref_session (reference_id, session_id)
-- issuances(issuance_id PK, reference_id, session_id, agent_id, audience,
--           tool, class, ttl_seconds, issued_at, expires_at, secret_hash,
--           single_use, consumed_at, provenance_json, status)
--   unique: issuances_binding_once (binding_hash, window)   -- §6 exactly-once
--   index:  issuances_session (session_id, status)
-- revocations(revocation_id PK, scope, target_id, requested_by,
--             requested_at, effective_at, reason, epoch_after)
-- backends(backend_id PK, kind, display_name, capability_flags,
--          health, conformance_version, added_at)
-- redaction_receipts(receipt_id PK, subject_id, field, class, count,
--                     redactor_version, created_at)
-- ledger(seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id UNIQUE,
--        event_version, event_name, occurred_at, monotonic_ms,
--        session_id, agent_id, reference_id, issuance_id, binding_json,
--        ttl_seconds, principal, reason, severity,
--        prev_hash TEXT NOT NULL, hash TEXT NOT NULL)
--   index: ledger_session_seq (session_id, seq)
```

### Hash-chain columns

| Column | Meaning |
|---|---|
| `seq` | Monotonic position and append order (`AUTOINCREMENT`). |
| `prev_hash` | `hash` of the previous ledger row; the genesis row uses a fixed all-zero anchor. |
| `hash` | `H(canonical(row_without_hash) ‖ prev_hash)`. |

The chain makes the lifecycle record **tamper-evident**: a rewritten or reordered row fails
`agentkeys verify-log` (R6, E12).

### Single-writer semantics & migrations

- **Single writer** — one broker process owns the store; WAL allows concurrent readers, one writer.
- **Atomic issue** — resolution + issuance + ledger append happen in one transaction (`atomic_issue`); a
  `kill -9` mid-issue either commits all or none, and restart recovers.
- **Migrations** — `schema_version` drives additive migrations; an old store opens under a new binary by
  migrating forward, or **refuses loudly** — it never silently drops or rewrites data (E11).

## 6. Integrity rules

| Rule | Statement | Enforced by |
|---|---|---|
| **Append-only ledger** | Ledger rows are never updated or deleted; corrections are new events. | store contract, chain |
| **CAS on revocation** | Revocation is a compare-and-set on `sessions.revoke_epoch`; a concurrent revoke cannot lose. | store transaction |
| **Exactly-once issuance** | At most one live issuance per `binding_hash` in a window; a retry returns the same record. | unique index + `atomic_issue` |
| **Single-use secret** | `consumed_at` is set once, by CAS; a second use of the same secret is `exchange-rejected`. | store transaction |
| **Chain integrity** | `hash` recomputes from canonical row + `prev_hash`; a mismatch stops issuance and raises `tamper`. | `verify-log` |
| **No secrets stored** | No column holds secret material; only `secret_hash` and class labels. | redactor + schema review (E5) |
| **Monotonic narrowing** | An issuance never has a wider audience/tool/class than its reference + binding allow. | mint path (E3, E14) |

> **Implemented (M3, 2026-11-09).** The config keys below are validated by `src/agentkeys/config.py`;
> the backend registry + failure semantics are implemented in `src/agentkeys/backends/`; see the
> [backends reference](../reference/backends.md).

## 7. Config keys

Configuration is declarative and **integrity-checked at session start**; ambiguity is fail-closed (E4).

| Key | Type | Meaning |
|---|---|---|
| `backends` | list | Registered backends + precedence; each must pass conformance (E9) |
| `ttl.<class>.floor` | seconds | Minimum honored TTL per class; a TTL below floor is rejected (fail closed) |
| `ttl.<class>.ceiling` | seconds | Maximum honored TTL per class; never silently extended (fail closed) |
| `bindings` | list | Allowed `(reference, audience, tool)` combinations |
| `enforce_mode` | enum | `monitor` \| `enforce` — evasion handling (R7) |
| `sink` | string | agentwatch sink endpoint; empty = local ledger only |
| `store.path` | path | SQLite database location |
| `clock.skew_tolerance` | seconds | Bounded tolerance before fail-closed (E6) |

Example class bounds (illustrative defaults, **not field-tested**): `public` ∈ [30, 900]s, `dev` ∈
[30, 900]s, `staging` ∈ [60, 600]s, `prod` ∈ [30, 300]s. A value outside `[floor, ceiling]` is **rejected at
load** — the broker never clamps silently into an unsafe direction.

## 8. Data lifecycle

| Aspect | Policy |
|---|---|
| **What is stored** | References (opaque), bindings, issuances (hashed secret only), sessions, revocations, lifecycle events, backend registry, redaction receipts. |
| **What is never stored** | Secret material of any kind; raw tool arguments containing secrets (redacted with receipts, E5); browser/session credentials (permanent refusal). |
| **Retention** | Ledger is append-only. Retention is local and policy-driven; pruning is an explicit, logged operation (a new event), never a silent delete. Default windows are **not yet** finalized. |
| **Export** | `agentkeys export --session <id>` / `--reference <id>` emits a deterministic, ordered **JSONL** timeline (principal, binding, timestamps, reasons, hash chain); a scan finds **zero** secrets (R6, E12). |
| **Redaction receipts** | Any masked field yields a `RedactionReceipt` (field, class, count); receipts travel with the events they annotate. |
| **Verify** | `agentkeys verify-log` recomputes the chain and reports integrity, gap markers, and any detected tamper. |
| **Evidence consumers** | Compliance tooling (agentcomply) consumes the secret-free export; no separate PII store is created. |

> Every item above is a **documented** design. There is **no** field-tested evidence yet. Retention windows
> and any cloud-backed store are explicitly open questions.

## 9. Cross-links

- Components, lifecycle, trust boundaries, failure semantics: [PRD 02 — Architecture](02-architecture.md).
- Invariants, STRIDE, stdio boundary, what we never store: [PRD 06 — Security Baseline](06-security-baseline.md).
- Requirements, acceptance criteria, feature catalog: [PRD 05 — Features](05-features.md).
- Personas and journeys behind these entities: [PRD 04 — Users & CUJs](04-users-and-cujs.md).
- Standards the contracts align to: [PRD 20 — Standards & Claims](20-standards-and-claims.md).
