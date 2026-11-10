# Contracts design — `akref/1.0`, `issuance/1.0`, resolution (M2)

**Status:** design of record for M2 · **Issue:** #30 (`2.D0`) · **Written before implementation.**
**Sources:** [PRD 15 §2-§4](../../prd/15-data-model.md), [PRD 18 §1-§3](../../prd/18-issuance-integrity.md),
[PRD 02 §2](../../prd/02-architecture.md), [store design](store.md).

**BLUF:** M2 fixes the two wire contracts — the **reference** (`akref/1.0`, opaque and loggable) and the
**issuance** (`issuance/1.0`, bound and single-use) — and the **resolution pipeline** that connects them to
the M1 store. Nothing is injected at egress yet: the token is minted, recorded, and consumed, not delivered.

A contract field can never carry plaintext secret material; that is schema-reviewed here and fixture-tested.

---

## 1. Package layout

| File | Contents |
|---|---|
| `src/agentkeys/contracts/reference.py` | `ReferenceDoc` (`akref/1.0`), validation, JSON round-trip |
| `src/agentkeys/contracts/issuance.py` | `Binding`, `IssuanceDoc` (`issuance/1.0`), TTL bounds validation |
| `src/agentkeys/contracts/registry.py` | the reference registry + the strict `akref:` grammar |
| `src/agentkeys/core/resolution.py` | the resolution pipeline (identity chain order), idempotency, use/consume |
| `src/agentkeys/sdk.py` | the embedder control surface — **no `get_secret()` exists** |
| `tests/contracts_fixtures.py` | shared builders |

## 2. `akref/1.0` — the reference

Fields exactly per PRD 15 §2: `akref` (the string `"1.0"`), `reference_id`, `backend`, `path`, `class`,
`scope_hint?`, `label?`.

Rules:
- `class` ∈ `public | dev | staging | prod`.
- All of `reference_id`, `backend`, `path` non-empty; **unknown fields are ignored** (additive, E11).
- **Opaque + loggable:** a string field whose value is secret-shaped (the same detector the M0 config
  validator uses) is rejected, and `path` must be a *slot name*, never a value (`--token=…`, `BEGIN …`)
  is rejected. The JSON may be printed, logged, and dumped into a context-dump: it yields nothing usable.
- `to_json()` is deterministic (sorted keys) so exports and receipts are diffable.

The `akref:` **grammar** (registry keys): `akref:<backend>/<path>` where `<backend>` matches
`[a-z][a-z0-9_-]*` and `<path>` matches `[A-Za-z0-9._/-]+` with no `..` segment. A malformed key is refused
**naming the failing part**; an unregistered but well-formed key is an `UnknownReference` (a rejection, not
a silence).

## 3. `issuance/1.0` — the issuance

Fields exactly per PRD 15 §3: `issuance`, `issuance_id`, `reference_id`, `session_id`, `agent_id`,
`binding: {audience, tool}`, `class`, `ttl`, `issued_at`, `expires_at`, `provenance?`.

Rules:
- `binding` = the triple `(audience, tool, session_id)`; `session_id` is a top-level field, the other two
  live in `binding`. Together they are the **ceiling**: an issuance is never broader (PRD 18 P2).
- `ttl` must lie within `[ttl.<class>.floor, ttl.<class>.ceiling]` from the M0 config; a value outside is
  **rejected at construction** (never clamped, never silently extended — fail closed, PRD 15 §7).
- `secret_hash` is **not** a wire field. It lives only in the store (`issuances.secret_hash`).
  `IssuanceDoc` has no field that could hold a token, a secret, or a plaintext value — asserted by test.
- `provenance = {decided_by, decision}` is present only for a higher-class mint (step-up, M10).

## 4. The identity chain (what M2 implements, and what it defers)

| Hop | M2 status |
|---|---|
| Reference identity (broker asserts; authorizes *which secret*) | **implemented** (registry) |
| Agent/session identity (broker asserts at session start) | **implemented** (store `sessions`; the SDK requires a `session_id`) |
| Subject (human, asserted by agentpolicy) | recorded as `provenance`; decided in **M10** |
| Actor (workload identity) | at v0.1.0 the OS principal of the broker channel; SPIFFE/WIMSE is **R12** (v0.2.0) |
| Execution credential (broker mints; one audience/tool/session/use) | **implemented** (mint + single-use consume) |

The pipeline order (§5) is normative; each check short-circuits to a typed denial.

## 5. Resolution pipeline (order is normative)

`ResolutionCore.resolve(reference_id, audience, tool, session_id, now?)`:

| # | Check | Failure |
|---|---|---|
| 1 | session exists and is **unrevoked** (`revoke_epoch == 0`) | `ResolutionDenied("session-revoked" / "unknown-session")` |
| 2 | reference is registered and the request's class is enabled | `UnknownReference` with the failing shape named |
| 3 | `(reference, audience, tool)` is an allowed binding in config | `ResolutionDenied("binding-not-allowed")` |
| 4 | class gate: M2 requires no approval (step-up is M10); a class marked `requires_approval` denies with `step-up-required` | `ResolutionDenied("step-up-required")` |
| 5 | compute `binding_hash = H(reference_id ‖ audience ‖ tool ‖ session_id)` and `window = now // window_seconds` | — |
| 6 | **idempotent**: if an issuance exists for `(binding_hash, window)`, return it (no new mint, no new event) | — |
| 7 | mint a **128-bit** token (`secrets.token_hex(16)`), store only `H(token)` via `store.issue` (atomic with the ledger row) | — |

Returns `ResolvedIssuance(issuance: IssuanceDoc, token: str | None)`.

**Why `token` may be `None`:** the plaintext token exists only transiently (I1). The core caches it in
process, keyed by `issuance_id`, and only while the issuance is live and unconsumed. A retry in the same
process returns the same token; across processes the retry returns the same issuance record with
`token=None` — the audit trail is identical, and nothing durable ever held a token. The mint is idempotent
(E1); the *token* is transient by design.

`window_seconds` is an injected policy (default 60s) — the store treats the window as an opaque integer.

## 6. Use and single-use consumption

`ResolutionCore.use(issuance_id, token, now?)`:
1. look up the issuance; unknown → `UseResult("unknown")`.
2. the presented token must hash-equal the stored `secret_hash` (constant-time compare). A mismatch is
   `UseResult("rejected")` — **a replay/fabrication attempt, never a silent pass**.
3. `store.consume(issuance_id, now)` is the CAS: `consumed` (once), `already_consumed` (replay),
   `expired`, `unknown`. The core drops the cached token on `consumed`.

A second use of the same token therefore returns `already_consumed` — the `exchange-rejected` outcome of
SC-08-SC-11, whose agentwatch event is emitted by the caller (M4/M7) from this typed result.

## 7. The registry

`ReferenceRegistry(store)`:
- `register(doc) -> ReferenceDoc` — validates, then `store.create_reference` (idempotent; a conflict is
  refused rather than overwritten).
- `get(key) -> ReferenceDoc` — `akref:<backend>/<path>` grammar-checked; unknown → `UnknownReference`.
- `list() -> tuple[ReferenceDoc, ...]`.
- **Enumeration-probe honesty:** the registry does not enumerate to an unauthenticated caller (M2's callers
  are in-process and OS-authenticated); evasion detection over probes is M9's job. M2 records only that a
  lookup missed (no secret, no value).

## 8. SDK / CLI surface (2.6)

`agentkeys.sdk.Broker` is the embedder contract: `register_reference`, `resolve`, `use`, `revoke`,
`list_references`, `get_issuance`. **There is no `get_secret()` and no method returning a stored
credential**; the only token a caller ever sees is the transient single-use one from `resolve`, and
`revoke` is unconditional (I3).

CLI (implemented in M2, the rest stay honest stubs): `agentkeys ref list`, `agentkeys ref show <id>` —
read-only, secret-free, `--json` envelope.

## 9. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 2.1 | `tests/test_reference_contract.py` | fields validate; class enum enforced; secret-shaped value rejected; unknown fields ignored; JSON round-trip is deterministic |
| 2.2 | `tests/test_issuance_contract.py` | binding triple; TTL below floor / above ceiling rejected; **no plaintext field exists** (attribute scan); secrets cannot be constructed-in |
| 2.3 | `tests/test_registry.py` | grammar accepted/refused with the failing part named; unknown key rejected; registration idempotent; conflict refused |
| 2.4 | `tests/test_resolution_idempotency.py` | retry within the window returns the same issuance and appends no event; a new window mints new |
| 2.5 | `tests/test_issuance_single_use.py` | token round-trips only via hash; second use `already_consumed`; wrong token `rejected`; expired token `expired` |
| 2.6 | `tests/test_sdk_cli_contract.py` | no `get_secret`-like attribute; `ref list`/`ref show` work; session-scoped resolve |

## 10. Review

Settled here: (1) the issuance document never carries `secret_hash` or a token; (2) idempotency is keyed by
`(binding_hash, window)` with the window an injected policy; (3) the transient token is never durable, and
`token=None` on a cross-process retry is the honest answer; (4) a token mismatch is a typed `rejected`, not
an exception; (5) the registry refuses unknown keys loudly. Deferred: step-up (M10), egress delivery
(M4/M5), evasion probes (M9), receipts (M3).

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `2.CR`.