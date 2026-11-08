# WBS v0.1.0 — Part 2: Contracts & Backends (M2–M3)

**BLUF:** **M2 fixes the wire contracts** — the `akref/1.0` reference and the `issuance/1.0` issuance with
the audience/tool/session binding and idempotent resolution (E1, E3) — so nothing later invents its own
shape. **M3 then gives the storage side the same rigor** ([R5](../../prd/05-features.md)): the pluggable
`Backend` contract ([E9](../../prd/05-features.md)) with OS-keychain + credential-file drivers, the
**fail-closed engine** ([E4](../../prd/05-features.md)), and redaction-by-default with receipts
([E5](../../prd/05-features.md)). Proven by the backend conformance suite and the fail-closed fault matrix.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M2 — Reference + issuance contracts + idempotent resolution (E1, E3)

**Goal:** the broker can register a **reference** and produce a **bound, single-use issuance** from it
idempotently — the contract everything above depends on, with the identity chain of
[PRD 18 §2](../../prd/18-issuance-integrity.md) as the design. No egress yet; the token is minted and
recorded, not injected.

**CUJ:** [CUJ-3](../../prd/04-users-and-cujs.md) (context-dump), [CUJ-5](../../prd/04-users-and-cujs.md)
(bindings), [CUJ-13](../../prd/04-users-and-cujs.md) (embedder) · **Requirements:**
[E1](../../prd/05-features.md), [E3](../../prd/05-features.md), [R1](../../prd/05-features.md),
[R3](../../prd/05-features.md), [PRD 18 §2–§3](../../prd/18-issuance-integrity.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 2.D0 | **Design docs first** | Contracts design: `akref/1.0`, `issuance/1.0`, the identity chain, the resolution pipeline order ([PRD 18 §3](../../prd/18-issuance-integrity.md)) | docs | reviewed before code | #30 | — | — |
| 2.1 | `akref/1.0` model + validation | Reference fields (backend, path, class, scope_hint, label); JSON Schema; **opaque + loggable** rule (no secret bytes) | contract module + schema | fixture references validate; a reference carrying a secret-shaped value is rejected | #31 | [CUJ-3](../../prd/04-users-and-cujs.md) | [R1](../../prd/05-features.md) |
| 2.2 | `issuance/1.0` model + binding | Issuance fields; binding = `(audience, tool, session)`; TTL within class floor/ceiling; `secret_hash` only, never plaintext | contract module + schema | TTL outside `[floor,ceiling]` rejected; no plaintext field exists | #32 | [CUJ-5](../../prd/04-users-and-cujs.md) | [R3](../../prd/05-features.md) |
| 2.3 | Reference registry + grammar | Register/list references; **strict grammar**; an unknown reference is a rejection with the shape named | registry module | unknown/ malformed reference → rejected; enumeration probe detectable | #33 | [CUJ-3](../../prd/04-users-and-cujs.md) | [R1](../../prd/05-features.md), [E1](../../prd/05-features.md) |
| 2.4 | Idempotent resolution | Resolve keyed by `(reference, binding)` within a window: a retry returns the **same** issuance and mints nothing new | resolution core | duplicate resolve returns the same record; exactly-once per binding | #34 | [CUJ-13](../../prd/04-users-and-cujs.md) | [E1](../../prd/05-features.md) |
| 2.5 | Single-use secret + consumption | 128-bit secret, stored **hashed**, consumed once by CAS; second use → `exchange-rejected` | issuance core | second consume fails; `consumed_at` set once | #35 | [CUJ-5](../../prd/04-users-and-cujs.md) | [E3](../../prd/05-features.md) |
| 2.6 | SDK / CLI contract surface | Stable out-of-process control surface (ask resolve/issue/revoke); **no `get_secret()` exists** | SDK + CLI | a host app issues/uses via the contract; no secret read-out path | #36 | [CUJ-13](../../prd/04-users-and-cujs.md) | [E1](../../prd/05-features.md) |
| 2.T | Tests | Contract validation, idempotency, single-use, grammar | tests | coverage ≥95% | #37 | — | — |
| 2.C | Coverage gate | ≥95% on contract modules | coverage report | ≥95% | #38 | — | — |
| 2.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #39 | — | — |
| 2.CR | Code review | Findings resolved | review log | no open findings | #40 | — | — |
| 2.D | Docs | Reference + issuance contracts in [PRD 15](../../prd/15-data-model.md); [PRD 12](../../prd/12-traceability.md) rows wired | docs | docs updated + linked | #41 | — | — |
| 2.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 2.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] The reference + issuance contracts are frozen; resolution is idempotent; consumption is single-use
- [ ] No contract field can carry a plaintext secret (schema-reviewed + fixture-tested)

**Planned (opens at `2.D0`).** Design: [`docs/design/v0.1.0/contracts.md`](../../design/v0.1.0/) · Scenarios:
[SC-08–SC-11](../../prd/17-scenarios.md), [SC-40](../../prd/17-scenarios.md) · Tests:
`tests/test_contract.py`, `tests/test_idempotency.py`, `tests/test_issuance_single_use.py`.

---

## Milestone M3 — Backends + fail-closed engine + redactor (R5, E4, E9, E5)

**Goal:** the storage side done to the same standard: one `Backend` contract with OS-keychain and
credential-file drivers, the **fail-closed** engine (no path from a failure to a credential), and
redaction-before-persistence with receipts. Rotation-without-restart
([CUJ-10](../../prd/04-users-and-cujs.md)) falls out of references re-resolving.

**CUJ:** [CUJ-8](../../prd/04-users-and-cujs.md) (fail-closed), [CUJ-10](../../prd/04-users-and-cujs.md)
(rotate) · **Requirements:** [R5](../../prd/05-features.md), [E4](../../prd/05-features.md),
[E9](../../prd/05-features.md), [E5](../../prd/05-features.md), [PRD 02 §6](../../prd/02-architecture.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 3.D0 | **Design docs first** | Backend contract, failure semantics, redaction vocabulary + receipt format | docs | reviewed before code | #42 | — | — |
| 3.1 | `Backend` interface | `resolve(reference) → secret`, `list`, `health` + capability flags; semantics: **never-log, resolve-at-use, fail-closed on ambiguity** | interface module | mypy-clean protocol; a capability-failing backend refuses at load | #43 | — | [E9](../../prd/05-features.md) |
| 3.2 | Keychain driver | macOS Keychain / Linux Secret Service; unlock-per-resolve; no plaintext disk write | driver | resolve/list/health pass the conformance suite | #44 | — | [R5](../../prd/05-features.md) |
| 3.3 | Credential-file driver | 0600 credential file fallback; loud `doctor` warning when used | driver | conformance passes; perms enforced under `umask 000` | #45 | — | [R5](../../prd/05-features.md) |
| 3.4 | **Backend conformance suite** | All backends behind one suite: resolve-at-use, never-log, fail-closed on locked/absent/ambiguous/slow, capability flags | fixtures | both drivers green; a fake broken backend **fails** | #46 | — | [E9](../../prd/05-features.md) |
| 3.5 | **Fail-closed engine** | Locked/absent/ambiguous backend → **deny issuance** with a structured reason; never a static/env fallback; `doctor` explains | engine | the fail-closed fault matrix is 100% deny-or-pending | #47 | [CUJ-8](../../prd/04-users-and-cujs.md) | [E4](../../prd/05-features.md) |
| 3.6 | Redactor + receipts | Pattern+shape redactor (API keys, bearer, private keys, conn strings, cloud creds) before storage/render/export; a receipt per masked field | redactor module | evidence scanner finds 0 secrets in store/export; receipts on every masked field | #48 | — | [E5](../../prd/05-features.md) |
| 3.T | Tests | Driver units + backend conformance + fault matrix + redactor | tests | coverage ≥95% | #49 | — | — |
| 3.C | Coverage gate | ≥95% on backend/engine/redactor modules | coverage report | ≥95% | #50 | — | — |
| 3.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #51 | — | — |
| 3.CR | Code review | Findings resolved | review log | no open findings | #52 | — | — |
| 3.D | Docs | [PRD 15 §7](../../prd/15-data-model.md) config; backend matrix + failure semantics; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #53 | — | — |
| 3.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 3.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Both backends pass the same conformance suite; a broken backend fails it
- [ ] Every failure path is deny-or-pending ([SC-18–SC-23](../../prd/17-scenarios.md)); 0 secrets in store/export

**Planned (opens at `3.D0`).** Design: [`docs/design/v0.1.0/backends.md`](../../design/v0.1.0/) · Scenarios:
[SC-06/SC-18–SC-23](../../prd/17-scenarios.md) · Tests: `tests/test_backend_keychain.py`,
`tests/test_backend_file.py`, `tests/test_failclosed_matrix.py`, `tests/test_redactor_receipts.py`.

---

Part 2 green ⇒ contracts are frozen and storage is fail-closed; proceed to
[Part 3 (M4–M5)](wbs-v0.1.0-part3-egress-stdio.md).
