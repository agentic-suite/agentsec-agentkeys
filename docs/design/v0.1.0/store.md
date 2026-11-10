# Store design — the BrokerStore contract (v0.1.0, M1)

**Status:** design of record for M1 · **Issue:** #18 (`1.D0`) · **Written before implementation.**
**Sources:** [PRD 15 §5–§7](../../prd/15-data-model.md), [PRD 13 §3/§5](../../prd/13-non-functional-requirements.md),
[PRD 02 §6](../../prd/02-architecture.md).

**BLUF:** The store is the broker's truth. This document freezes **one typed contract** — the `BrokerStore`
protocol — plus its six hard semantics (idempotent issue, CAS revoke, single-use consume, gapless
hash-chained ledger, exactly-once recovery, durable-commit-before-ack) and two drivers (SQLite reference,
memory). No core, backend, or CLI path may touch state except through this contract; the **conformance
suite is the contract's executable form** and a deliberately broken driver must fail it.

This document is the source of truth for M1. A divergence is a bug in the code, not an amendment here.

---

## 1. Layering and the one-state-path rule

```text
CLI / resolution core (M2) ──▶ BrokerStore (this contract) ──▶ SQLite (reference) | memory
```

- The store is the **only** component that reads or writes persisted state. Backends (§M3) resolve
  secrets; they never write the store. Ledger events are appended through `append_event`, never by a
  driver side effect.
- Everything is **typed**: `mypy --strict` clean, no `Any` at the boundary. Integers only for time
  (`epoch` seconds, `monotonic_ms` where the row carries it).

## 2. Package layout

| File | Contents |
|---|---|
| `src/agentkeys/store/contract.py` | frozen dataclasses, `BrokerStore` Protocol, `CapabilityFlags`, errors, `require_capabilities` |
| `src/agentkeys/store/memory.py` | `MemoryStore` (dicts + lock; ephemeral) |
| `src/agentkeys/store/sqlite.py` | `SqliteStore` (WAL, `synchronous=FULL`, file perms) |
| `src/agentkeys/store/schema.py` | DDL, `CURRENT_SCHEMA_VERSION`, forward-only migrations |
| `src/agentkeys/store/loader.py` | driver selection via the `agentkeys.store` entry-point group |
| `tests/store_conformance.py` | the conformance suite (`run_conformance(factory)` → findings) |
| `tests/conformance_fakes.py` | deliberately broken drivers used to prove the suite fails them |

## 3. Data model (the typed records)

Frozen dataclasses; fields are exactly the PRD 15 §5 columns. No field can hold plaintext secret material —
`issuances.secret_hash` is a hash and every other column is metadata (invariant I7).

```text
CapabilityFlags(single_writer, durable, atomic_issue, cluster_safe)   # all bool

Reference(reference_id, akref_version, backend, path, class_, scope_hint, label,
          created_at, created_by)

Session(session_id, agent_id, harness, started_at, ended_at, status,
        revoke_epoch, principal)

Binding(binding_hash, reference_id, audience, tool, session_id,
        first_seen_at, issuance_count)

Issuance(issuance_id, binding_hash, window, reference_id, session_id, agent_id,
         audience, tool, class_, ttl_seconds, issued_at, expires_at,
         secret_hash, single_use, consumed_at, provenance_json, status)

Revocation(revocation_id, scope, target_id, requested_by, requested_at,
           effective_at, reason, epoch_after)

LedgerEvent(event_id, event_version, event_name, occurred_at, monotonic_ms,
            session_id, agent_id, reference_id, issuance_id, binding_json,
            ttl_seconds, principal, reason, severity)

LedgerRow(seq, event, prev_hash, hash)          # seq assigned by the store

RedactionReceipt(receipt_id, subject_id, field, class_, count,
                 redactor_version, created_at)   # table created in M1, written in M3
```

`window` (integer) is the **idempotency bucket** for a binding: the M2 resolution core computes it from
the TTL window; the store only enforces uniqueness of `(binding_hash, window)`. Keeping the bucket
explicit means the store never has to know about clocks or TTL policy.

## 4. The `BrokerStore` contract

```python
class BrokerStore(Protocol):
    def capabilities(self) -> CapabilityFlags: ...
    def open(self) -> None: ...
    def close(self) -> None: ...

    # references
    def create_reference(self, reference: Reference) -> Reference: ...   # idempotent by reference_id
    def get_reference(self, reference_id: str) -> Reference | None: ...
    def list_references(self) -> tuple[Reference, ...]: ...

    # sessions
    def create_session(self, session: Session) -> Session: ...
    def get_session(self, session_id: str) -> Session | None: ...
    def get_binding(self, binding_hash: str) -> Binding | None: ...

    # issuance (atomic: binding + issuance + ledger row in one transaction)
    def issue(self, *, reference_id: str, session_id: str, agent_id: str, audience: str,
              tool: str, class_: str, ttl_seconds: int, window: int, secret_hash: str,
              single_use: bool, issued_at: int, provenance_json: str,
              binding_hash: str, event: LedgerEvent) -> Issuance: ...
    def get_issuance(self, issuance_id: str) -> Issuance | None: ...
    def find_issuance(self, binding_hash: str, window: int) -> Issuance | None: ...
    def consume(self, issuance_id: str, *, now: int) -> ConsumeResult: ...
    def list_live(self, now: int) -> tuple[Issuance, ...]: ...

    # revocation (CAS on sessions.revoke_epoch)
    def cas_revoke(self, *, scope: str, target_id: str, requested_by: str, requested_at: int,
                   reason: str, event: LedgerEvent) -> RevokeResult: ...
    def get_revocation(self, revocation_id: str) -> Revocation | None: ...

    # ledger
    def append_event(self, event: LedgerEvent) -> LedgerRow: ...
    def read_ledger(self, since_seq: int = 0) -> tuple[LedgerRow, ...]: ...
    def export_session(self, session_id: str) -> tuple[LedgerRow, ...]: ...

    # receipts (written in M3; created here so the schema is stable)
    def add_receipt(self, receipt: RedactionReceipt) -> RedactionReceipt: ...
    def list_receipts(self, subject_id: str) -> tuple[RedactionReceipt, ...]: ...
```

`ConsumeResult` is a frozen dataclass: `status: Literal["consumed", "already_consumed", "expired", "unknown"]`
plus the `Issuance | None`. A second consume is never an exception — it is a typed result the caller maps
to `exchange-rejected` (SC-08–SC-11). `RevokeResult` carries the effective `Revocation`, `winner: bool`, and
`epoch_before`/`epoch_after`.

The store **mints** the ids for state it creates (`iss_…` for an issuance, `rev_…` for a revocation) and
rewrites the ledger event's `issuance_id` accordingly, so the evidence row and the state row never disagree.

`issue` takes its ledger event as a parameter so the **one transaction** covers binding + issuance +
ledger (PRD 15 §5 "atomic issue"), and the store assigns `seq`/`hash` for the appended row.

## 5. Semantics (normative — the conformance suite asserts each)

| # | Semantic | Statement |
|---|---|---|
| S1 | **Idempotent issue** | At most one issuance per `(binding_hash, window)`. A repeat `issue` with the same key returns the **existing** record and mints nothing new; `bindings.issuance_count` does not double-count the retry. |
| S2 | **CAS revoke** | `cas_revoke` is a compare-and-set on `sessions.revoke_epoch`: exactly one concurrent caller wins; `epoch_after = epoch_before + 1`, strictly monotonic, never reused. A losing caller returns the winner's revocation (`winner: false`) — revocation is never lost, and is never policy-gated. |
| S3 | **Single-use consume** | `consume` sets `consumed_at` exactly once by CAS. A second call returns `already_consumed`; a call after `expires_at` returns `expired`; an unknown id returns `unknown`. |
| S4 | **Gapless hash-chained ledger** | `seq` is contiguous from 1; `hash = H(canonical(event) ‖ prev_hash)`; genesis `prev_hash` is 64 zeros. Ledger rows are never updated or deleted. |
| S5 | **Exactly-once recovery** | After a crash mid-issue, the store holds **either** the whole issuance **or** none of it — never a binding without an issuance, nor an issuance without its ledger row. A retry then succeeds exactly once. |
| S6 | **Durable-commit-before-ack** | `issue` returns only after the transaction is committed (fsync'd in SQLite). Nothing is acknowledged that a crash could lose. |

**Capability refusal.** `require_capabilities(store, needed)` raises `CapabilityError` naming the missing
flag. The resolution core requires `atomic_issue`; anything requiring crash-durability requires `durable`.
A driver lacking a required capability is refused — there is no degraded mode (fail closed, I2).

**Window.** `window = issued_at // window_seconds`, computed by the caller (M2) from the class TTL; the
store treats it as an opaque integer. The unique index is `(binding_hash, window)`.

## 6. Schema (SQLite, DDL) and versioning

```sql
CREATE TABLE schema_version (version INTEGER NOT NULL);
-- one row; written on first migration only

CREATE TABLE references (
  reference_id TEXT PRIMARY KEY, akref_version TEXT NOT NULL, backend TEXT NOT NULL,
  path TEXT NOT NULL, class TEXT NOT NULL, scope_hint TEXT, label TEXT,
  created_at INTEGER NOT NULL, created_by TEXT NOT NULL);
CREATE INDEX references_backend_path ON references (backend, path);

CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, harness TEXT NOT NULL,
  started_at INTEGER NOT NULL, ended_at INTEGER, status TEXT NOT NULL,
  revoke_epoch INTEGER NOT NULL DEFAULT 0, principal TEXT NOT NULL);
CREATE INDEX sessions_agent ON sessions (agent_id, status);

CREATE TABLE bindings (
  binding_hash TEXT PRIMARY KEY, reference_id TEXT NOT NULL, audience TEXT NOT NULL,
  tool TEXT NOT NULL, session_id TEXT NOT NULL, first_seen_at INTEGER NOT NULL,
  issuance_count INTEGER NOT NULL DEFAULT 0);
CREATE INDEX bindings_ref_session ON bindings (reference_id, session_id);

CREATE TABLE issuances (
  issuance_id TEXT PRIMARY KEY, binding_hash TEXT NOT NULL, window INTEGER NOT NULL,
  reference_id TEXT NOT NULL, session_id TEXT NOT NULL, agent_id TEXT NOT NULL,
  audience TEXT NOT NULL, tool TEXT NOT NULL, class TEXT NOT NULL,
  ttl_seconds INTEGER NOT NULL, issued_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
  secret_hash TEXT NOT NULL, single_use INTEGER NOT NULL, consumed_at INTEGER,
  provenance_json TEXT NOT NULL, status TEXT NOT NULL,
  UNIQUE (binding_hash, window));                       -- S1 exactly-once
CREATE INDEX issuances_session ON issuances (session_id, status);
CREATE INDEX issuances_expiry  ON issuances (expires_at);   -- live-by-expiry

CREATE TABLE revocations (
  revocation_id TEXT PRIMARY KEY, scope TEXT NOT NULL, target_id TEXT NOT NULL,
  requested_by TEXT NOT NULL, requested_at INTEGER NOT NULL, effective_at INTEGER NOT NULL,
  reason TEXT NOT NULL, epoch_after INTEGER NOT NULL);

CREATE TABLE backends (
  backend_id TEXT PRIMARY KEY, kind TEXT NOT NULL, display_name TEXT NOT NULL,
  capability_flags TEXT NOT NULL, health TEXT NOT NULL, conformance_version TEXT NOT NULL,
  added_at INTEGER NOT NULL);

CREATE TABLE redaction_receipts (
  receipt_id TEXT PRIMARY KEY, subject_id TEXT NOT NULL, field TEXT NOT NULL,
  class TEXT NOT NULL, count INTEGER NOT NULL, redactor_version TEXT NOT NULL,
  created_at INTEGER NOT NULL);
CREATE INDEX receipts_subject ON redaction_receipts (subject_id);

CREATE TABLE ledger (
  seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
  event_version TEXT NOT NULL, event_name TEXT NOT NULL, occurred_at INTEGER NOT NULL,
  monotonic_ms INTEGER NOT NULL, session_id TEXT, agent_id TEXT, reference_id TEXT,
  issuance_id TEXT, binding_json TEXT, ttl_seconds INTEGER, principal TEXT,
  reason TEXT, severity TEXT NOT NULL, prev_hash TEXT NOT NULL, hash TEXT NOT NULL);
CREATE INDEX ledger_session_seq ON ledger (session_id, seq);
```

**Versioning.** `CURRENT_SCHEMA_VERSION = 1` in `schema.py`; M0's `doctor` already reads this table.
`open()` reads the version and applies forward migrations in order inside one transaction. A store whose
version is **greater** than `CURRENT_SCHEMA_VERSION` refuses loudly (`StoreVersionError`) — never a silent
downgrade, never a dropped column (E11). An empty file migrates from 0 → 1.

**File permissions.** On create: the containing directory is created `0700` and the store is `0600`
(enforced with an explicit `chmod` so `umask 000` cannot widen it). WAL/SHM files inherit the store's mode.

**Concurrency.** SQLite in WAL: many readers, one writer; `BEGIN IMMEDIATE` for write transactions;
`PRAGMA synchronous=FULL` so S6 holds. A second writer process receives `sqlite3.OperationalError:
database is locked` within `busy_timeout`; the store maps it to `StoreBusyError` (deny, not retry-forever).

**Test-only crash hook (S5).** The SQLite driver honours `AGENTKEYS_TEST_CRASH_POINT`:
`after_write_before_commit` calls `os._exit(70)` inside the transaction. It is documented as a test hook,
is inert unless the variable is set to a known value, and exists so the recovery fixture can kill a real
process mid-write and assert all-or-none. No production path reads it.

## 7. Drivers

| Driver | Flags | Notes |
|---|---|---|
| `sqlite` (reference) | `single_writer=True, durable=True, atomic_issue=True, cluster_safe=False` | WAL, `synchronous=FULL`, perms as above; `:memory:` allowed for tests but reports `durable=False` |
| `memory` | `single_writer=True, durable=False, atomic_issue=True, cluster_safe=False` | dicts behind a lock; ephemeral; used for tests and embedded use |

Both drivers pass the **same** conformance suite. `sqlite` with a `:memory:` path is a third configuration
in the suite (it must still honour S1–S3 and S6-within-process).

## 8. Driver selection (entry points)

Group `agentkeys.store`; built-ins declared in `pyproject.toml`
(`sqlite = "agentkeys.store.sqlite:SqliteStore"`, `memory = "agentkeys.store.memory:MemoryStore"`).

- `load_driver(name, **kwargs) -> BrokerStore` looks the name up in the group; an unknown name is a
  **usage error** (`DriverNotFound`, exit `1`) naming the known drivers.
- A driver is admitted only if it exposes the contract surface and declares `capabilities()`.
  `require_capabilities` then refuses it when a needed flag is missing (**denied**, exit `2`).
- Third-party drivers are admitted the same way; full behavioural conformance is gated by the milestone
  conformance kit (M11, E13) — this loader gates shape + capability declaration only, and says so.

## 9. Test plan (the conformance suite is the contract)

`tests/store_conformance.py` exposes `run_conformance(factory) -> list[Finding]` covering S1–S6 plus:
unknown-id reads, duplicate `create_reference`, `list_live` filtering by expiry/consumption, ledger
ordering and gaplessness, `export_session` scoping, receipt round-trip, and capability refusal.

- `tests/test_store_conformance.py` parametrizes `sqlite` (file), `sqlite:memory`, and `memory`; all must
  report **zero** findings.
- `tests/conformance_fakes.py` provides `BrokenIssueStore` (not idempotent), `BrokenLedgerStore`
  (gap in seq), `BrokenConsumeStore` (double-consume allowed), and `AmoebaStore` (declares `durable=True`
  but drops writes). The suite must report a finding for each — proving the suite can fail.
- `tests/test_store_recovery.py` spawns a subprocess that issues under
  `AGENTKEYS_TEST_CRASH_POINT=after_write_before_commit`, asserts all-or-none, then retries exactly once.
- `tests/test_store_perms.py` asserts `0700` dir / `0600` store under `umask 000`.
- `tests/test_store_migrations.py` opens a v0 store, migrates to 1, and asserts a v2 store refuses
  (`StoreVersionError`).

## 10. Review

Self-review against PRD 15 §5–§6, PRD 13 §3 (durability) and §5 (portability), PRD 02 §6 (fail closed),
and the M1 WBS table. Decisions settled here: (1) the idempotency `window` is an explicit caller-supplied
integer, so the store holds no clock/TTL policy; (2) the ledger event is a parameter of `issue`/`cas_revoke`
so one transaction covers state + evidence; (3) `consume` returns a typed result rather than raising;
(4) exactly-once recovery is proven with a real `os._exit` behind a test-only env hook, not a mock;
(5) capability refusal is a hard deny with no degraded mode. Deferred: backend registry *population*
(M3), redaction receipt *writing* (M3), full third-party conformance gating (M11).

Code review findings are recorded in [`docs/wbs/v0.1.0/codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `1.CR`.