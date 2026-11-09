# Code review log — v0.1.0

**BLUF:** Every milestone closes with a `.CR` work item: review findings are recorded here and resolved
before the milestone gate. This log is **append-only** and **hand-written** — it is evidence, so no
automation writes, rewrites, or summarizes it ([AGENTS.md](../../../AGENTS.md): the hand-maintained-report
rule applies to review findings too). A milestone with an open finding is not closed.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## How findings are recorded

One section per milestone, appended at `.CR`. Each finding: **id · severity (blocker/major/minor) ·
location · what · resolution · status**. A finding stays open until its resolution is a commit ref. A
public-surface finding (a security invariant, a contract, a claim) is a **blocker** — the milestone does not
close until it is resolved or the design is amended to match reality.

## Finding classes we treat as blockers

- A path from any failure to a credential (breaks I2, [PRD 06 §1](../../prd/06-security-baseline.md)).
- A plaintext secret reachable in store/export/ledger/log (breaks I1/I7).
- A replay/forward/widening that succeeds (breaks I4).
- A revocation that is TTL-waiting or policy-gated (breaks I3, D-07).
- A claim that outruns its evidence label ([PRD 20 §6](../../prd/20-standards-and-claims.md)).
- A secret found anywhere by the audit — including **git history** ([Part 8 M15](wbs-v0.1.0-part8-fieldtest-release.md)).

## Findings

### 0.CR — Foundation & identity (2026-11-09)

- **CR-001** · minor · `src/agentkeys/cli.py` · `ArgumentParser.error` overrode a `Never`-returning
  method with `-> None`, so `mypy --strict` failed · fixed: `-> NoReturn` · `757f256` · RESOLVED
- **CR-002** · major · `src/agentkeys/config.py` · nested-key validation errors named only the leaf
  (`path must be a string`) instead of the dotted key, weakening the "actionable error names the failing
  field" NFR · fixed: `_require_*` take a `label` and `store.path` / `clock.skew_tolerance` report dotted ·
  `757f256` · RESOLVED
- **CR-003** · major · `src/agentkeys/config.py` · `ttl = 5` reached `_parse_ttl` and raised
  `AttributeError` (a crash, not a fail-closed denial) · fixed: non-table `ttl` is a `ConfigError` ·
  `757f256` · RESOLVED
- **CR-004** · blocker · `src/agentkeys/config.py` · a literal secret could reach the parse path because
  the pattern scan ran before key validation but a secret in a *list* element (`bindings[].reference`) was
  untested; a gap here would let a secret persist (I1/I7) · fixed: recursive scan covers lists; test
  asserts the secret is rejected and never echoed · `757f256` · RESOLVED
- **CR-005** · minor · `.github/workflows/ci.yml` · the first cut risked being a placeholder that never
  gated coverage; a docs-as-test now asserts every gate step is present · `afc1133`, `757f256` · RESOLVED
- **CR-006** · minor · `Makefile` · targets hard-coded `.venv/bin`, so the same targets could not run in
  CI · fixed: `PYTHON` resolves the venv when present, else PATH · `757f256` · RESOLVED

No open findings. The milestone's public-surface invariants (fail-closed config, references-only,
reserved exit codes, doctor exit precedence) each have a gating test.

### 1.CR — BrokerStore contract + drivers (2026-11-09)

- **CR-007** · blocker · `src/agentkeys/store/schema.py` · the `references` table name is a SQLite
  keyword; unquoted DDL/statements raised `near "references": syntax error`, so **no store could open**
  (the truth layer did not exist) · fixed: the table and its statements are quoted · `dac066b` · RESOLVED
- **CR-008** · blocker · `src/agentkeys/store/schema.py` · `migrate()` used `executescript`, which commits
  implicitly; the following `ROLLBACK` failed and a partially applied migration could survive (a schema
  built halfway, then used) · fixed: statements are applied individually inside one explicit
  `BEGIN IMMEDIATE`/`COMMIT` per migration · `dac066b` · RESOLVED
- **CR-009** · major · `src/agentkeys/store/sqlite.py` · `cas_revoke` rolled back in its `except` block and
  the caller's handler rolled back again, so `sqlite3.OperationalError: cannot rollback` replaced the real
  denial — a fail-closed reason lost and an untyped error escaping the store · fixed: one rollback, in the
  handler only · `dac066b` · RESOLVED
- **CR-010** · major · `src/agentkeys/store/schema.py` · a store file with tables but no `schema_version`
  (a corrupt or foreign database) was entered, a version table was created inside it, and migration then
  raised a raw `sqlite3.OperationalError` — neither loud nor fail-closed · fixed: refuse loudly naming
  `schema_version` · `2590b97` · RESOLVED
- **CR-011** · major · `tests/store_conformance.py` · every check shared one store, so a file-backed
  driver saw another check's issuance on the retry path — the suite could pass a driver that violates S1
  (or fail a conformant one), which would have made the contract gate untrustworthy · fixed: each check
  runs in its own namespace key; the suite now provably fails four deliberately broken drivers ·
  `040f7e8` · RESOLVED
- **CR-012** · minor · `src/agentkeys/store/{sqlite,memory}.py` · duplicate `receipt_id`/`event_id` surfaced
  raw SQLite `UNIQUE constraint failed: …` text instead of a named error · fixed: named
  `duplicate receipt_id` / `duplicate event_id` · `dac066b` · RESOLVED
- **CR-013** · minor · `src/agentkeys/store/sqlite.py` · a test-only crash hook is risk-bearing; it is
  accepted only because it is inert unless `AGENTKEYS_TEST_CRASH_POINT=after_write_before_commit` is set,
  and a test asserts it is inert without the variable · `dac066b` · RESOLVED
- **CR-014** · minor · `src/agentkeys/store/sqlite.py` · `:memory:` reports `durable=False` and is skipped
  by the durability check, so a `:memory:` store can never masquerade as durable · `040f7e8` · RESOLVED

No open findings. Every semantic (S1-S6) has a gating fixture; the
[conformance suite](../../reference/store-conformance.md) is the contract's executable form.

### 2.CR — Reference + issuance contracts (2026-11-09)

- **CR-015** · blocker · `src/agentkeys/contracts/issuance.py` · an early draft reused the storage record as
  the wire document, which would have put `secret_hash` (and, via repr, a token) one step from the caller's
  context · fixed: the wire document is a distinct type with no secret field, asserted by an attribute scan,
  and `ResolvedIssuance.__repr__` redacts the token · `6ddef6d`, `fd2eeeb` · RESOLVED
- **CR-016** · major · `src/agentkeys/core/resolution.py` · a token mismatch could have been reported as
  `already_consumed` (a pass-shaped result) if the hash compare were skipped · fixed: constant-time
  `hmac.compare_digest` first, with a distinct `rejected` outcome and its own test · `6ddef6d` · RESOLVED
- **CR-017** · major · `src/agentkeys/contracts/issuance.py` · TTL was validated by the caller only, so a
  misconfigured window could mint an over-broad token · fixed: `validate_ttl` runs on the mint path and the
  issuance constructor refuses an `expires_at` that is not `issued_at + ttl` · `0ec2150` · RESOLVED
- **CR-018** · minor · `src/agentkeys/contracts/reference.py` · a secret-shaped `path`/`label` would have
  been serialised into a context-dump · fixed: the shared `looks_like_secret` detector refuses such values,
  and the reference module reuses the M0 detector rather than duplicating patterns · `28cc831` · RESOLVED
- **CR-019** · minor · `src/agentkeys/commands/ref.py` · a missing config initially returned a usage code,
  which conflated "you typed it wrong" with "the broker cannot run safely" · fixed: a missing/invalid config
  is a **denial** (exit 2), tested · `fd2eeeb` · RESOLVED
- **CR-020** · minor · `src/agentkeys/sdk.py` · the embedder surface is the likeliest place for a
  `get_secret()` to be added later; a test asserts no public name contains "secret"/"plaintext" and the
  class refuses unknown attributes with a named reason · `fd2eeeb` · RESOLVED

No open findings. Idempotency (E1) and single-use (E3) each have gating fixtures, and the "no plaintext
field" rule is asserted structurally rather than by convention.

### 3.CR — Backends + fail-closed engine + redactor (2026-11-09)

- **CR-021** · blocker · `src/agentkeys/backends/contract.py` · a backend could have returned a bare `str`,
  which would then flow into a log or an error message · fixed: `resolve` returns a `SecretValue` whose
  `repr`/`str`/`format` are redacted and which refuses comparison to a string; the conformance suite fails a
  driver that returns a string · `630e764`, `1611516` · RESOLVED
- **CR-022** · blocker · `src/agentkeys/backends/file.py` · the credential file was read once at `open`, so
  a rotation would have kept serving the **old** secret (CUJ-10 broken, stale credential held in memory) ·
  fixed: the file is re-read on every `resolve`, with permissions re-checked; the engine caches nothing ·
  `8128f3b` · RESOLVED
- **CR-023** · major · `src/agentkeys/backends/file.py` · permissions were validated only at `open`, so a
  mode widened afterwards was invisible · fixed: `_check_permissions` runs at open and at every resolve,
  and the conformance suite asserts `0600` for file-backed drivers · `8128f3b` · RESOLVED
- **CR-024** · major · `tests/backends_conformance.py` · an early check asserted that any backend denies when
  "locked", which every correct driver trivially failed; the suite would have reported false findings ·
  fixed: the generic locked check was removed (locking is exercised by the fault matrix at `3.5`) and the
  list-leak check now compares against the value the driver actually resolves · `1611516` · RESOLVED
- **CR-025** · major · `src/agentkeys/backends/keychain.py` · a missing `security`/`secret-tool` binary raised
  a raw `FileNotFoundError` out of `resolve`, escaping the denial vocabulary · fixed: mapped to
  `BackendUnavailable`, with a test · `7744166` · RESOLVED
- **CR-026** · minor · `src/agentkeys/redact.py` · class ordering classified `Authorization: Bearer <jwt>`
  as a `jwt` rather than a `bearer` span, so the receipt under-reported the field's nature · fixed: bearer
  patterns precede the jwt pattern · `3.6` · RESOLVED
- **CR-027** · minor · `src/agentkeys/config.py` · the M0 secret patterns would have become a second,
  drifting copy of the redactor's · fixed: `looks_like_secret` is imported from `agentkeys.redact` and a
  test asserts the objects are identical · `3.6` · RESOLVED
- **CR-028** · minor · `src/agentkeys/backends/keychain.py` · `subprocess` with an argv list is correct, but
  the audit trail needed the reasoning recorded · documented in-line: fixed argv, no shell, slot from
  trusted config, never from agent input · `3.6` · RESOLVED

No open findings. The fault matrix is 100% deny-or-pending, both drivers pass one shared conformance suite,
and the redactor's pattern set is the single source shared with M0/M2.

<!--
Template:

## 0.CR — Foundation & identity (2026-..-..)

- **CR-001** · blocker · `agentkeys/config.py` · config could fall back to a literal secret on a parse
  ambiguity · fixed: ambiguity is a hard failure with the field named · `abc1234` · RESOLVED
-->
