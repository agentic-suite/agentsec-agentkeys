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

### 4.CR — Egress-injection engine (2026-11-09)

- **CR-029** · blocker · `src/agentkeys/egress/contract.py` · the passthrough rule was only a convention: a
  driver could have put `request.client_token` into its output and nothing would have noticed · fixed:
  `BaseInjector.apply` inspects the delivered material, raises `passthrough-stripped`, and marks
  `overwrote_client_credential`; each driver has a test with a client-supplied token · `(4.1)` · RESOLVED
- **CR-030** · blocker · `src/agentkeys/egress/exchange.py` · an exchange could have used the *client's* token
  as `subject_token`, silently forwarding it upstream (E14 violation) · fixed: the subject is the broker's
  single-use token, the client token is refused if it appears in the request body, and the test asserts it is
  absent · `(4.4)` · RESOLVED
- **CR-031** · major · `src/agentkeys/egress/contract.py` · audience was checked against the *request* only,
  so an injector configured for another audience would have accepted a mismatched issuance · fixed: the
  injector's own audience is compared too, and `check_injection` covers the injector-side case · `(4.5)` · RESOLVED
- **CR-032** · major · `src/agentkeys/egress/header.py` · leaving a client-supplied credential header in place
  would have sent both credentials, letting the downstream pick the attacker's · fixed: credential-family
  headers are removed before the bound one is set · `(4.3)` · RESOLVED
- **CR-033** · major · `src/agentkeys/core/sessions.py` · an unbounded session would have let a second agent
  inherit the first agent's binding · fixed: `SessionBinder` refuses a different agent and a revoked session,
  and a new session starts unbound · `(4.6)` · RESOLVED
- **CR-034** · minor · `tests/test_inject_exchange.py` · the fake exchange treated an empty response as
  "absent", so the failure path was never exercised · fixed: an explicit empty response is honoured and the
  denial is asserted · `(4.4)` · RESOLVED
- **CR-035** · minor · `src/agentkeys/egress/exchange.py` · a hard-coded `actor_token` default needed a
  security-scanner justification; documented as an identifier, never a secret · `(4.4)` · RESOLVED

No open findings. Every refusal path returns a typed reason and emits `exchange-rejected`; the four rules
each have a gating test.

### 5.CR — stdio MCP credential virtualization (2026-11-09)

- **CR-036** · blocker · `src/agentkeys/stdio/substitute.py` · stripping client credentials ran before
  placeholder substitution, so the documented pattern (`GITHUB_TOKEN=akref:…`) would have been *dropped*
  instead of virtualized — the flagship's primary use case silently lost its token · fixed: a placeholder is
  a reference, not a credential; only a **literal** value in a credential variable is stripped, and both
  behaviours are tested · `(5.3/5.4)` · RESOLVED
- **CR-037** · blocker · `src/agentkeys/stdio/proxy.py` · the child's stderr was drained only after stdin
  closed; a chatty server could fill the pipe and deadlock the proxy · fixed: stderr is drained on its own
  thread · `(5.2)` · RESOLVED
- **CR-038** · major · `src/agentkeys/stdio/proxy.py` · an oversized frame could have been forwarded
  truncated (a malformed JSON-RPC message to the server) · fixed: `forward_frame` refuses the frame, the
  proxy logs the refusal to stderr and forwards nothing · `(5.2)` · RESOLVED
- **CR-039** · major · `src/agentkeys/stdio/wrapper.py` · the child environment was the caller's environment;
  the broker's own environment (including any harness-injected credential) would have been inherited · fixed:
  the child env is built by explicit substitution + stripping, with a virtualization marker · `(5.1)` · RESOLVED
- **CR-040** · major · `src/agentkeys/commands/run.py` · the CLI minted tokens without recording a `use`
  event, so a stdio issuance had no evidence trail · fixed: each substitution appends a `use` event in the
  session · `(5.1)` · RESOLVED
- **CR-041** · minor · `src/agentkeys/stdio/proxy.py` · `assert`-based pipe checks vanished under `-O`,
  turning a programming error into an obscure `AttributeError` · fixed: an explicit `RuntimeError` · `(5.2)` · RESOLVED
- **CR-042** · minor · `src/agentkeys/stdio/substitute.py` · a malformed placeholder was passed through to the
  child; a typo could therefore send the literal string `akref:…` (or worse, a value) to a server · fixed:
  the key grammar is checked before substitution; a malformed placeholder is refused · `(5.3)` · RESOLVED

No open findings. The co-located-runtime limit is documented as a first-class property
([stdio virtualization](../../reference/stdio-virtualization.md)), not a footnote.

### 6.CR — Revocation + kill-time + time correctness (2026-11-09)

- **CR-043** · major · `src/agentkeys/core/resolution.py` · `use()` never consulted the session epoch, so a
  token minted before a revoke could still be consumed at its next hop · fixed: `use()` reads the session
  and returns `rejected` when the epoch is set · `(6.1/6.5)` · RESOLVED
- **CR-044** · major · `src/agentkeys/revoke.py` · `RevokeOutcome.events` included an event for a **losing**
  CAS that the store never wrote — evidence for something that did not happen · fixed: only won revocations
  contribute an event · `(6.6)` · RESOLVED
- **CR-045** · minor · `src/agentkeys/commands/replay.py` · the narrowed issuance id relied on `assert`,
  which vanishes under `-O` · fixed: an explicit `None` guard exits `DENIED` · `(6.3)` · RESOLVED

### 7.CR — Ledger + events + export (2026-11-09)

- **CR-046** · major · `src/agentkeys/events.py` · `EventEmitter.build` passed `occurred_at` twice when a
  caller supplied a stamp, raising a `TypeError` on an otherwise valid event · fixed: explicit stamps win
  (`setdefault`) · `(7.2)` · RESOLVED
- **CR-047** · minor · `src/agentkeys/export.py` · an export parent directory was created with the default
  mode · fixed: best-effort `0700` (the export is already secret-free) · `(7.3)` · RESOLVED

### 8.CR — Scan + migrate (2026-11-09)

- **CR-048** · major · `src/agentkeys/scan.py` · the scanner flagged the `KEY=akref:…` line it had just
  written (the env-assignment shape), so a migrated finding never closed on re-scan · fixed: reference
  values are excluded from findings · `(8.2/8.4)` · RESOLVED
- **CR-049** · major · `src/agentkeys/migrate.py` · the reference was registered **before** the file
  rewrite, leaving a dangling reference when a rewrite failed · fixed: register last; on failure restore
  every file and delete the just-written backend slot · `(8.3)` · RESOLVED
- **CR-050** · minor · `src/agentkeys/scan.py` · the file text was re-split for every candidate (quadratic
  on large files) · fixed: split once per file · `(8.1)` · RESOLVED

### 9.CR — Evasion + tamper (2026-11-09)

- **CR-051** · major · `src/agentkeys/evasion.py` · an enforcer exception could have been read as a block
  in `enforce` mode — a claimed block that never happened · fixed: any enforcer failure is a **named gap**
  (`blocked=False`, `gap_named=True`) · `(9.3)` · RESOLVED
- **CR-052** · minor · `src/agentkeys/tamper.py` · enumeration probes accumulate across sessions inside the
  window · accepted: a global probe signal is the intended detection; the per-session attribution is on
  every event · `(9.6)` · RESOLVED (documented)

### 10.CR — Step-up + recipes (2026-11-09)

- **CR-053** · major · `src/agentkeys/core/resolution.py` · `step-up-granted` was written **before** the
  mint, so a failed mint could leave a grant with no issuance · fixed: the grant is emitted after the store
  transaction and carries the new `issuance_id` · `(10.2)` · RESOLVED

No open findings.

### 11.CR — Conformance kit + evidence + invariants + supply chain (2026-11-09)

- **CR-054** · major · `src/agentkeys/invariants.py` · the I5 probe compared the token against
  `event.reason`, which is `None` on most rows, raising `TypeError` and marking a **healthy** broker red ·
  fixed: compare against `(reason or "")` · `(11.3)` · RESOLVED
- **CR-055** · minor · `src/agentkeys/conformance.py` · the failure handler caught
  `(AssertionError, InjectionDenied, Exception)` — redundant and misleading about what is caught · fixed:
  a single `Exception` with the "assertions included" note · `(11.1)` · RESOLVED
- **CR-056** · major · `src/agentkeys/evidence.py` · receipts were unreachable through the store contract
  (`list_receipts` needs a subject), so "receipts present" could not be verified · fixed: additive
  `list_all_receipts()` in both drivers · `(11.2)` · RESOLVED

### 12.CR — Operations (2026-11-09)

- **CR-057** · major · `src/agentkeys/ops.py` · restore compared the backup schema against
  `SqliteStore(":memory:").schema_version()`, which is `None` before `open()` — every restore raised
  `TypeError` · fixed: compare with `CURRENT_SCHEMA_VERSION` · `(12.2)` · RESOLVED
- **CR-058** · major · `src/agentkeys/doctor.py` · the new chain check treated a store with no `ledger`
  table as tamper, so a healthy fresh store failed `doctor` · fixed: an absent ledger is "no ledger yet" ·
  `(12.4)` · RESOLVED
- **CR-059** · minor · `src/agentkeys/ops.py` · nested `with` blocks made the backup/restore transaction
  bounds hard to read · fixed: a single multi-context `with` · `(12.2)` · RESOLVED

### 13.CR — Docs completion (2026-11-09)

- **CR-060** · minor · `docs/design/v0.1.0/*.md`, `docs/prd/appendix-a-consolidated-prd.md` · the new
  doc-link check found pre-existing broken relative links (design docs pointed at `../prd`, appendix at
  sibling repositories) · fixed: links corrected to `../../prd`; unresolvable external source citations kept
  as plain labels · `(13.T)` · RESOLVED
- **CR-061** · major · `docs/tutorials/quickstart.md` · the brokered-call step implied a token was injected
  without a placeholder, which the wrapper does not do · fixed: the documented `NAME=akref:…` placeholder
  pattern, exercised by the step test · `(13.3)` · RESOLVED

No open findings.

### 14.CR — Field-test harness + report (2026-11-09)

The milestone review covers the field-test tooling (`src/agentkeys/fieldtest/`, `scripts/fieldtest/`,
`field-test/v0.1.0/docker/`) and the sweep's findings. **Product defects: zero.** Every finding below was in
the harness or the environment, found by the gates, fixed with a test or re-run.

- **CR-062** · blocker · `src/agentkeys/fieldtest/runner.py` · `fingerprint()` ran `git`/`docker`
  unconditionally and crashed inside containers where neither exists, killing the in-container packs ·
  fixed: guarded `FileNotFoundError`/`OSError` → `"unavailable"` · `(14.1)` · RESOLVED
- **CR-063** · blocker · `src/agentkeys/fieldtest/packs_docker.py` · the air-gap leg mounted a named volume
  root-owned and the non-root broker user (UID 10001) could not create its results dir → FT-DK-AIRGAP
  FAIL · fixed: root-user `mkdir`+`chown` prep step, then run as 10001 · re-run PASS · `(14.3)` · RESOLVED
- **CR-064** · major · `src/agentkeys/fieldtest/packs_core.py` · FT-CL-HEADER stored
  `Authorization: Bearer <token>` verbatim in the committed assertion → **a real secret shape in the
  evidence** · fixed: assert booleans, never rendered header values; leak gate re-run clean · `(14.2)` · RESOLVED
- **CR-065** · major · `src/agentkeys/fieldtest/packs_core.py` · FT-RK-INFLIGHT asserted
  `list_live(0) == 0` after revoke — a wrong belief (revoke is an epoch CAS, not a status flip) · fixed:
  assert the `revoked` event was recorded + next-hop refused · `(14.4)` · RESOLVED
- **CR-066** · major · `src/agentkeys/fieldtest/packs_core.py` · FT-CL-FIRST's fresh-venv leg installed
  into a home whose config pointed at the *original* store path → the fresh CLI read a stale store ·
  fixed: `_quickstart_config(home, reference)` parameterizes the config · `(14.2)` · RESOLVED
- **CR-067** · major · `src/agentkeys/fieldtest/packs_attack.py` · the live Claude Code leg used
  `claude -p --mcp-config <file> <prompt>` (prompt parsed as the config path) and did not detect the
  unauthenticated state · fixed: `--mcp-config <file> -p <prompt>`; detect "Not logged in" → honest WARN
  with the named limitation · `(14.7)` · RESOLVED
- **CR-068** · major · `src/agentkeys/fieldtest/gates.py` · deep validation enforced assertion minimums on
  NOT-RUN cases (docker cases under `--no-docker` have zero assertions) → false findings · fixed: skip the
  count rule for `not-run` (reason + limitation still required) · `(14.T)` · RESOLVED
- **CR-069** · minor · `src/agentkeys/fieldtest/packs_docker.py` · `compose run --network none` is not a
  compose v2 flag; the child image ENTRYPOINT swallowed the boundary probe · fixed: plain
  `docker run --network none` and an explicit `--entrypoint sh` · `(14.3)` · RESOLVED
- **CR-070** · minor · `src/agentkeys/fieldtest/packs_docker.py` · the scan service lacked
  `AGENTKEYS_FIELD_ROOT` + the repo mount → `cases.yaml` not found · fixed in compose · `(14.3)` · RESOLVED
- **CR-071** · minor · `src/agentkeys/fieldtest/packs_core.py` · `_FAKE_TOKEN`/`_FAKE_SECRET` constants
  tripped S105 and could echo into artifacts · renamed `_PLANTED_VALUE`, never interpolated into assertions ·
  `(14.2)` · RESOLVED
- **CR-072** · minor · `scripts/fieldtest/*` · the gate self-test risked exercising destructive gates on the
  real results · fixed: every gate self-test runs on a temp copy only · `(14.T)` · RESOLVED

No open findings. The report-guard test proves the hand-maintained report cannot be written by any script;
the sweep edited it by hand under the user's explicit instruction.

<!--
Template:

## 0.CR — Foundation & identity (2026-..-..)

- **CR-001** · blocker · `agentkeys/config.py` · config could fall back to a literal secret on a parse
  ambiguity · fixed: ambiguity is a hard failure with the field named · `abc1234` · RESOLVED
-->
