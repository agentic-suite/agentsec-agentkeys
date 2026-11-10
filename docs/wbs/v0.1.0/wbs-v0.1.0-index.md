# WBS — agentkeys v0.1.0 (Index)

**BLUF:** v0.1.0 delivers the **entire never-in-context credential lifecycle with zero external
dependencies**: the `akref/1.0` reference + `issuance/1.0` contract with idempotent resolution, the
pluggable BrokerStore (SQLite WAL + memory, capability-flagged), the keychain + credential-file backends
with the **fail-closed** engine, the three egress-injection drivers (**env-virtualization**, **HTTP
header**, **RFC 8693 exchange**), the **stdio MCP virtualization** nobody else ships (coverage row #8),
**`revoke` ≤1s** replay-verified + the hash-chained lifecycle ledger + agentwatch events, **secret-evasion
detection**, **`agentkeys scan`/`migrate`**, **step-up issuance** via agentpolicy, ≥2 Tier-1 harness
recipes, the conformance kit, and the supply-chain floor (signed release, SBOM, Scorecard). **M15's
release-readiness gate includes the security audit — `trufflehog` + a full git-history scan for token
leakage — and tags `v0.1.0`.** **Sixteen milestones (M0–M15)** across **eight detail files — two
milestones per file**; **the final two milestones are field tests (M14) and release readiness (M15)**.
v0.1.0 is the [PRD 05](../../prd/05-features.md) §A/§B P0 set only (R1–R9 + R17 + E1–E15).

> **Milestone ranges by intent:** **M0–M1** = foundation + truth layer (packaging, CLI, exit codes,
> config, store) · **M2–M3** = contracts + backends (reference/issuance, keychain/file, fail-closed,
> redaction) · **M4–M5** = egress (three drivers; the stdio flagship) · **M6–M7** = revoke + evidence
> (kill-time ≤1s, ledger, events) · **M8–M9** = hygiene + hardening (scan/migrate, evasion, tamper) ·
> **M10–M11** = approvals + reach (step-up, recipes, conformance kit, supply chain) · **M12–M13** = ops +
> docs (service units, backup/restore, runbooks; reference, quickstart, recipes) · **M14–M15** = **the**
> field test + release. The WBS builds the whole set to one release; nothing in the forward slate
> (R10–R19, P1/P2) is in scope — those get their own WBS at v0.1.x.

## Standard milestone exit criteria (applies to EVERY milestone)

Every milestone is worked in this order:

1. **Design docs written first** — the milestone's `.D0` work item opens it (design + reference docs for the
   subsystem, written before code).
2. **Implement** the milestone's work items (one ticket at a time: test first (RED) → implement (GREEN)).
3. **Close with the standing gates:**
   - [ ] **All tests pass** (`make test`) — the `.T` work item
   - [ ] **Coverage ≥ 95%** (enforced in CI) — the `.C` work item
   - [ ] **Lint strict clean** — `ruff` zero violations; `mypy --strict` clean — the `.L` work item
   - [ ] **Code review complete** — findings in [codereview-log.md](codereview-log.md), all resolved — `.CR`
   - [ ] **Docs updated** — design/reference docs + the [PRD 12](../../prd/12-traceability.md) requirement →
     test row moves with the work — `.D`
   - [ ] **Committed & pushed** — the work is on the feature branch — `.CI`
   - [ ] **WBS updated** — a dated checkpoint (commit refs + gate result) appended to the Progress section — `.W`

> Every milestone therefore carries **eight standing gate work items** — `.D0` design · `.T` tests · `.C`
> coverage · `.L` lint/types · `.CR` review · `.D` docs · `.CI` commit · `.W` WBS — in addition to its
> implementation items.

## Standard milestone closure (applies to EVERY milestone)

A milestone is **closed** only when all of these hold:

1. **Implemented** — every work item done; no "core slice", no partials.
2. **Tests green** — the milestone's tests pass, and the standard gates run **once at milestone end** (full
   suite, coverage ≥95%, `ruff`, `mypy --strict`) — not per ticket.
3. **Committed & pushed** — the work is on the feature branch, pushed.
4. **Tracking issue closed** — or explicitly commented with status.
5. **Docs updated** — the milestone's design/reference docs updated and linked from this WBS.
6. **Checkpoint recorded** — a dated line appended to the Progress section (commit refs + gate result).
7. **The final two milestones are field tests (M14) and release readiness (M15)** — **M15 tags `v0.1.0`**;
   nothing follows M15.

> **One ticket at a time:** per work item, write the test first (RED) → implement (GREEN) → next. Do **not**
> run the full suite between tickets; run it at milestone end only. A ticket that cannot complete is marked
> **BLOCKED** with the reason, never reported as done ([AGENTS.md](../../../AGENTS.md)).

## Milestones

| M | Name | Detail file |
|---|---|---|
| **M0** | **Foundation & identity** (fresh build: packaging, CLI, reserved exit codes, config, CI, `doctor`) | [Part 1](wbs-v0.1.0-part1-foundation-store.md) |
| M1 | BrokerStore contract + SQLite/memory drivers (E2, E11) | [Part 1](wbs-v0.1.0-part1-foundation-store.md) |
| M2 | Reference `akref/1.0` + issuance `issuance/1.0` contract + idempotent resolution (E1, E3) | [Part 2](wbs-v0.1.0-part2-contracts-backends.md) |
| M3 | Backend contract + keychain/file drivers + fail-closed engine + redactor (R5, E4, E9, E5) | [Part 2](wbs-v0.1.0-part2-contracts-backends.md) |
| M4 | Egress-injection engine: env / header / RFC 8693 (R2, R3, E7, E14) | [Part 3](wbs-v0.1.0-part3-egress-stdio.md) |
| M5 | **stdio MCP credential virtualization (flagship)** (R8, E7, E14) | [Part 3](wbs-v0.1.0-part3-egress-stdio.md) |
| M6 | Revocation + kill-time ≤1s + time correctness (R4, E6) | [Part 4](wbs-v0.1.0-part4-revoke-ledger.md) |
| M7 | Lifecycle ledger + agentwatch events + export/verify-log (R6, E12) | [Part 4](wbs-v0.1.0-part4-revoke-ledger.md) |
| M8 | Secret-hygiene `scan` + `migrate` (R17) | [Part 5](wbs-v0.1.0-part5-scan-evasion.md) |
| M9 | Secret-evasion detection + tamper resistance (R7, E10) | [Part 5](wbs-v0.1.0-part5-scan-evasion.md) |
| M10 | Step-up issuance + harness recipes (R9, E8) | [Part 6](wbs-v0.1.0-part6-stepup-conformance.md) |
| M11 | Conformance kit + supply chain + security hardening (E13, E15) | [Part 6](wbs-v0.1.0-part6-stepup-conformance.md) |
| M12 | Ops: service units, backup/restore, migrations, `doctor` hardening, drill tooling (PRD 22) | [Part 7](wbs-v0.1.0-part7-ops-docs.md) |
| M13 | Docs completion: reference, quickstart, runbooks, recipes (PRD 22/13, CUJ-1) | [Part 7](wbs-v0.1.0-part7-ops-docs.md) |
| **M14** | **Field tests — FINAL** (SC-01–SC-53; context-dump study; kill-time benchmark) | [Part 8](wbs-v0.1.0-part8-fieldtest-release.md) |
| **M15** | **Release readiness — FINAL** (incl. the **security audit: `trufflehog` + git-history token-leakage scan**); tags `v0.1.0` | [Part 8](wbs-v0.1.0-part8-fieldtest-release.md) |

## Issues & milestones (GitHub)

**Created 2026-11-08.** Every work item ships as a **GitHub issue** under milestone `0.1.0 — M<n> <name>` (labels `0.1.0`, `wbs`; gate items also `gate`). Body standard: Context · Why · What · How · Data & schema impact · Security & privacy · Edge cases · Testing · Risks & mitigations · Acceptance criteria · Dependencies · References · Definition of done; marker `<!-- wbs:<file>:<item> -->`. **The `Issue` column in each part file holds the live number.** The two process items per milestone (`.CI` commit, `.W` WBS checkpoint) are tracked here, not as issues.

**16 milestones · 194 issues** (`agentic-suite/agentsec-agentkeys`).

| M | Milestone | Issues |
|---|---|---|
| M0 | Foundation & identity | #5–#17 (13) |
| M1 | BrokerStore contract + drivers (E2, E11) | #18–#29 (12) |
| M2 | Reference + issuance contracts + idempotent resolution (E1, E3) | #30–#41 (12) |
| M3 | Backends + fail-closed engine + redactor (R5, E4, E9, E5) | #42–#53 (12) |
| M4 | Egress-injection engine: env / header / RFC 8693 (R2, R3, E7, E14) | #54–#65 (12) |
| M5 | stdio MCP credential virtualization (R8, E7, E14) | #66–#76 (11) |
| M6 | Revocation + kill-time ≤1s + time correctness (R4, E6) | #77–#88 (12) |
| M7 | Lifecycle ledger + agentwatch events + export/verify-log (R6, E12) | #89–#100 (12) |
| M8 | Secret-hygiene scan + migrate (R17) | #101–#111 (11) |
| M9 | Evasion detection + tamper resistance (R7, E10) | #112–#123 (12) |
| M10 | Step-up issuance + harness recipes (R9, E8) | #124–#135 (12) |
| M11 | Conformance kit + supply chain + security hardening (E13, E15) | #136–#147 (12) |
| M12 | Operations: service units, backup/restore, migrations, drills (PRD 22) | #148–#159 (12) |
| M13 | Docs completion: reference, quickstart, runbooks, recipes (PRD 22/13, CUJ-1) | #160–#171 (12) |
| M14 | Field tests — FINAL (SC-01–SC-53; study; benchmark) | #172–#185 (14) |
| M15 | Release readiness — FINAL (security audit + tag `v0.1.0`) | #186–#198 (13) |

## Progress

- **2026-11-08 — plan of record published.** No code yet. PRD set 00–23 + Appendix A complete
  ([PRD index](../../prd/README.md)); this WBS writes the build from it. Nothing checked off; the first
  milestone (M0) opens with `0.D0` (foundation design).
- **2026-11-09 — M0 Foundation & identity closed** (branch `feat-v0.1.0`). Items `0.D0` and `0.1`–`0.7`
  implemented test-first (RED → GREEN, one ticket at a time). Milestone gate run **once** at the end:
  `ruff` clean · `mypy --strict` clean · full suite green · coverage **98.97% ≥ 95%**. Commits:
  `4a6227b` (0.D0 design) · `06ed423` (0.1 packaging) · `9cabc83` (0.2 CLI) · `b5dd278` (0.3 exit codes) ·
  `549b731` (0.4 config) · `afc1133` (0.5 CI) · `518c670` (0.6 doctor) · `3e70d2d` (0.7 identity) ·
  `757f256` (gate coverage). `0.CR` logged 6 findings, all resolved ([codereview-log.md](codereview-log.md)).
  Docs: [foundation design](../../design/v0.1.0/foundation.md) · [CLI reference status](../../reference/cli.md) ·
  [PRD 12 §0](../../prd/12-traceability.md) wired. No credential is brokered yet. **Next: M1 opens at `1.D0`.**
- **2026-11-09 — M1 BrokerStore contract + drivers closed** (branch `feat-v0.1.0`). Items `1.D0`, `1.1`-`1.6`
  implemented test-first. Milestone gate run **once** at the end: `ruff` clean · `mypy --strict` clean ·
  full suite green (32 modules) · coverage **95.61% ≥ 95%**. Commits: `f461293` (1.D0 design) ·
  `da3aba1` (1.1 contract) · `d0465b5` (1.2 SQLite) · `5aeb470` (1.3 memory) · `040f7e8` (1.4 conformance) ·
  `2590b97` (1.5 migrations) · `dac066b` (1.6 loader + 1.T/1.C/1.L gate). `1.CR` logged 8 findings
  (3 blockers), all resolved ([codereview-log.md](codereview-log.md)). Docs:
  [store design](../../design/v0.1.0/store.md) · [store reference](../../reference/store.md) ·
  [conformance guide](../../reference/store-conformance.md) · [PRD 12 §0.1](../../prd/12-traceability.md).
  No credential is brokered yet. **Next: M2 opens at `2.D0`.**
- **2026-11-09 — M2 Reference + issuance contracts closed** (branch `feat-v0.1.0`). Items `2.D0`, `2.1`-`2.6`
  implemented test-first. Milestone gate run **once** at the end: `ruff` clean · `mypy --strict` clean ·
  full suite green · coverage **95.48% ≥ 95%**. Commits: `67c07c3` (2.D0 design + 2.1 akref) ·
  `0ec2150` (2.2 issuance) · `12448ab` (2.3 registry) · `6ddef6d` (2.4/2.5 resolution) ·
  `fd2eeeb` (2.6 SDK + CLI). `2.CR` logged 6 findings (1 blocker), all resolved. Docs:
  [contracts design](../../design/v0.1.0/contracts.md) · [contracts reference](../../reference/contracts.md) ·
  [PRD 15 §2 note](../../prd/15-data-model.md) · [PRD 12 §0.2](../../prd/12-traceability.md).
  A harness can now resolve a reference into a bound, single-use issuance — it is not yet injected at
  egress (M4/M5). **Next: M3 opens at `3.D0`.**
- **2026-11-09 — M3 Backends + fail-closed engine + redactor closed** (branch `feat-v0.1.0`). Items `3.D0`,
  `3.1`-`3.6` implemented test-first. Milestone gate run **once** at the end: `ruff` clean · `mypy --strict`
  clean · full suite green · coverage **96.71% ≥ 95%**. Commits: `630e764` (3.D0 + 3.1) · `f9e10dc` (3.2) ·
  `8128f3b` (3.3) · `1611516` (3.4) · `7744166` (3.5) · (3.6 with the gate). `3.CR` logged 8 findings
  (2 blockers), all resolved. Docs: [backends design](../../design/v0.1.0/backends.md) ·
  [backends reference](../../reference/backends.md) · [conformance guide](../../reference/backends-conformance.md) ·
  [PRD 12 §0.3](../../prd/12-traceability.md). Credentials can now be resolved fail-closed and redacted;
  they are still not delivered to a target at egress. **Next: M4 opens at `4.D0`.**
- **2026-11-09 — M4 Egress-injection engine closed** (branch `feat-v0.1.0`). Items `4.D0`, `4.1`-`4.6`
  implemented test-first. Milestone gate run **once** at the end: `ruff` clean · `mypy --strict` clean ·
  full suite green · coverage **96.43% ≥ 95%**. `4.CR` logged 7 findings (2 blockers), all resolved. Docs:
  [egress design](../../design/v0.1.0/egress.md) · [egress reference](../../reference/egress.md) ·
  [PRD 02 §4 note](../../prd/02-architecture.md) · [PRD 12 §0.4](../../prd/12-traceability.md).
  A minted issuance can now be injected into a child environment, an HTTP header, or an RFC 8693 exchange —
  with the audience enforced at the injector and no client-token passthrough. **Next: M5 opens at `5.D0`.**
- **2026-11-09 — M5 stdio MCP credential virtualization closed** (branch `feat-v0.1.0`) — the flagship.
  Items `5.D0`, `5.1`-`5.5` implemented test-first. Milestone gate run **once** at the end: `ruff` clean ·
  `mypy --strict` clean · full suite green · coverage **96.17% ≥ 95%**. `5.CR` logged 7 findings (2 blockers),
  all resolved. Docs: [stdio design](../../design/v0.1.0/stdio.md) ·
  [stdio virtualization reference](../../reference/stdio-virtualization.md) ·
  [ext-auth appendix](../../design/v0.1.0/stdio-ext-auth-appendix.md) ·
  [PRD 02 §5 note](../../prd/02-architecture.md) · [PRD 12 §0.5](../../prd/12-traceability.md).
  A stock stdio server now authenticates under the broker with references in its config and a scoped token at
  its egress; the co-located-runtime limit is documented, not hidden. **Next: M6 opens at `6.D0`.**
- **2026-11-09 — M6 Revocation + kill-time ≤1s + time correctness closed** (branch `feat-v0.1.0`).
  Items `6.D0`, `6.1`-`6.6` implemented test-first. `revoke` is a CAS on `revoke_epoch` (session/agent/all),
  `replay --last` proves the kill (exit `4` only on a refused replay), the kill-time harness reports
  p50/p95/max with p95 and max ≤1s, and `TimeGuard`/`ExpirySweeper` make a clock jump unable to extend or
  resurrect a TTL. Commits: `3d492b4`. Docs: [revoke design](../../design/v0.1.0/revoke.md) ·
  [revoke reference](../../reference/revoke.md). `6.CR` logged 3 findings, all resolved.
  **Next: M7 opens at `7.D0`.**
- **2026-11-09 — M7 Lifecycle ledger + agentwatch events + export/verify-log closed** (branch
  `feat-v0.1.0`). Items `7.D0`, `7.1`-`7.6` implemented test-first. The chain verifier names the first bad
  `seq`, the event emitter is allow-listed (`event_version` 1.0), `export` is deterministic 0600 JSONL,
  `verify-log` reports tamper as exit `3`, correlation exposes the join keys, and a sink outage leaves the
  local ledger authoritative with one `sink-gap` marker. Commit: `3d492b4`. Docs:
  [ledger design](../../design/v0.1.0/ledger.md) · [ledger reference](../../reference/ledger.md).
  `7.CR` logged 2 findings, both resolved. **Next: M8 opens at `8.D0`.**
- **2026-11-09 — M8 Secret-hygiene scan + migrate closed** (branch `feat-v0.1.0`). Items `8.D0`, `8.1`-`8.5`
  implemented test-first. The seeded corpus reaches **100% recall with 0 printed values**, broad reuse is
  flagged across files, `migrate` moves the value to the file backend and rewrites every site atomically
  (rollback on failure), and `--ci` refuses honestly as not-yet. Commit: `3d492b4`. Docs:
  [scan/migrate design](../../design/v0.1.0/scan-migrate.md) · [scan/migrate reference](../../reference/scan-migrate.md).
  `8.CR` logged 3 findings, all resolved. **Next: M9 opens at `9.D0`.**
- **2026-11-09 — M9 Evasion detection + tamper resistance closed** (branch `feat-v0.1.0`). Items `9.D0`,
  `9.1`-`9.6` implemented test-first. Raw reads are classified and recorded as high-severity events;
  enforce mode blocks only with a composed enforcer and **names the gap** otherwise; config integrity pins a
  digest and fails closed with `tamper-detected`; unknown-reference probes raise the enumeration signal.
  Commit: `1ebf136`. Docs: [evasion/tamper design](../../design/v0.1.0/evasion-tamper.md) ·
  [evasion reference](../../reference/evasion.md). `9.CR` logged 2 findings, both resolved.
  **Next: M10 opens at `10.D0`.**
- **2026-11-09 — M10 Step-up issuance + harness recipes closed** (branch `feat-v0.1.0`). Items `10.D0`,
  `10.1`-`10.6` implemented test-first. A prod-class mint requires an agentpolicy decision recorded in
  `provenance` (self-approval and free-text verdicts are refused; timeout = deny); the grant event is
  emitted after the mint and carries the issuance id. Claude Code (env) and Cursor (header) recipes use the
  same `agentkeys run` wrapper with reference-only env, and a smoke harness ends in an authenticated call;
  an uncovered harness is labelled not-yet. Commit: `1ebf136`. Docs:
  [step-up design](../../design/v0.1.0/stepup-recipes.md) · [step-up reference](../../reference/stepup.md) ·
  [recipes](../../guides/recipes/claude-code.md) · [PRD 12](../../prd/12-traceability.md).
  `10.CR` logged 1 finding, resolved.
- **2026-11-09 — M6–M10 milestone gate (run once, at the end).** `ruff` zero violations · `mypy --strict`
  clean (127 files) · full suite **582 passed** · coverage **95.45% ≥ 95%**. Test-first per ticket; no
  full-suite run between tickets. **Next: M11 opens at `11.D0`; M12–M15 remain.**
- **2026-11-09 — M11 Conformance kit + supply chain + security hardening closed** (branch `feat-v0.1.0`).
  Items `11.D0`, `11.1`-`11.6` implemented test-first. `agentkeys conformance` runs the RFC 8693/8707/9700/
  9728/9068/7636, backend, no-passthrough, and widening suites; DPoP is **not-supported**, never implied.
  The evidence scanner finds 0 secrets in a clean store and fails on a seeded leak (SC-43), all ten
  invariants have executable probes with red-when-violated fixtures, the four attack packs pass and go red
  when a gate is broken, the in-repo supply-chain floor is checked (stdlib-only deps, `security.txt`, CI
  gates, SBOM, fuzz targets), and core + revoke run with sockets disabled (SC-39). Docs:
  [design](../../design/v0.1.0/conformance-supplychain.md). `11.CR` logged 3 findings, all resolved.
  **Next: M12 opens at `12.D0`.**
- **2026-11-09 — M12 Operations closed** (branch `feat-v0.1.0`). Items `12.D0`, `12.1`-`12.6` implemented
  test-first. `serve` holds a `0600` lock, refuses a live holder, replaces a stale one, and removes the lock
  on SIGTERM; user-scoped launchd/systemd units are written with `--write-units` (no root). `backup` is a
  WAL-safe copy with a verified chain head + manifest; `restore` refuses a live broker, a broken chain, or a
  newer schema, and preserves the chain. Downgrades refuse loudly; `doctor` gained `chain`, `serve-lock`,
  and `config-integrity`; retention appends a marker and deletes nothing; the drill reports p50/p95/max.
  Docs: [ops design](../../design/v0.1.0/ops.md) · [ops reference](../../reference/ops.md).
  `12.CR` logged 3 findings, all resolved. **Next: M13 opens at `13.D0`.**
- **2026-11-09 — M13 Docs completion closed** (branch `feat-v0.1.0`). Items `13.D0`, `13.1`-`13.6`
  implemented test-first. CLI and config coverage tests fail on an undocumented flag/key and on a
  documented-but-absent one; the quickstart (`tests/docs/test_quickstart.py`) replays scan → migrate → ref →
  brokered call → revoke → replay (exit `4`) → export → verify-log; eight runbooks, the adapter recipes page,
  the operator guide, the honest-gaps page, and a doc-link check are live. Docs:
  [quickstart](../../tutorials/quickstart.md) · [config reference](../../reference/config.md) ·
  [runbooks](../../runbooks/rb-1-locked-backend.md) · [honest gaps](../../explanation/honest-gaps.md).
  `13.CR` logged 2 findings, both resolved.
- **2026-11-09 — M11–M13 milestone gate (run once, at the end).** `ruff` zero violations · `mypy --strict`
  clean (155 files) · full suite **656 passed** · coverage **95.23% ≥ 95%**. Test-first per ticket; no
  full-suite run between tickets. **Next: M14 opens at `14.D0` (field tests); M15 remains.**
- **2026-11-09 — M14 Field tests closed** (branch `feat-v0.1.0`). The plan, the 74-case registry, the runner,
  the deep-validation gates, the Docker topology, and the hand-maintained report all shipped; the sweep ran
  **74/74 verdicts: 71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN**. All five blocking scenarios PASS (kill-time
  p95 0.015ms / max 0.031ms at N=100; context-dump 0 usable with the control firing; tamper fail-closed;
  evidence clean with the seeded leak caught; scan/migrate 100% recall / 0 printed). The three WARN are the
  plan's `P/F|W` limitations, each named: fresh-machine install median needs a naive human (machine path
  measured at 2.7s), Claude Code not logged in headlessly, Cursor has no headless surface. The one FAIL that
  appeared (FT-DK-AIRGAP, a Docker volume-ownership harness bug) and the fixable WARN (FT-EV-ENFORCE, no
  enforcer composed) were **fixed and re-run green**. Published `bench/killtime-contextdump.json` + README.
  Results: `field-test/v0.1.0/results/` · plan/ report/ traceability: `docs/field-test/v0.1.0/`.
  `14.CR` logged 11 findings (CR-062…CR-072), all resolved; **zero product defects**.
- **2026-11-09 — M14 milestone gate (run once, at the end).** `ruff` zero violations · `ruff format --check`
  clean · `mypy --strict` clean (**177 files**) · full suite **743 passed** · coverage **95.22% ≥ 95%**
  (field-test tooling covered by pack-level execution tests). **Next: M15 opens at `15.D0` — security
  audit (`trufflehog` + full git-history scan), claims lint, compatibility matrix, SBOM + signing +
  Scorecard, tag `v0.1.0`.**

## PRD coverage matrix (every doc 00–23 + Appendix A)

| PRD | Topic | Milestone(s) |
|---|---|---|
| **PRD 00** | Press release / FAQ | narrative; validated at M15 |
| **PRD 01** | Why | context (all milestones) |
| **PRD 02** | Architecture (components, trust boundaries, failure semantics) | M0–M11 |
| **PRD 03** | Landscape (the unowned rows #7/#8) | M4–M6 (the capabilities) |
| **PRD 04** | Users, stories & CUJs (CUJ-1..14) | M2–M15 |
| **PRD 05** | Features R1–R9 + R17 + E1–E15 (v0.1.0 P0) | M0–M11 |
| **PRD 06** | Security baseline (invariants, threats, "we are a target") | M3, M9, M11, M15 (audit) |
| **PRD 07** | Success metrics (kill-time, zero-secret, migration funnel) | M6 (kill-time), M14 (study), M15 |
| **PRD 08** | Risks | cross-cutting; reviewed at M14 |
| **PRD 09** | Roadmap | M15 (release notes scope) |
| **PRD 10** | Feature parity | M15 (claims, no over-claim) |
| **PRD 11** | Decisions D-01..D-17 | cross-cutting (honored every milestone) |
| **PRD 12** | Traceability (maintained) | every milestone |
| **PRD 13** | NFRs (performance, durability, portability) | M1, M4, M6, M11 |
| **PRD 14** | Non-goals (scope guard — the forward slate is out of scope) | every milestone |
| **PRD 15** | Data model (`akref/1.0`, `issuance/1.0`, event set, schema) | M2–M3, M7 |
| **PRD 16** | Adapters & integration (recipes, drivers, backends, embedder) | M3–M5, M10 |
| **PRD 17** | Scenario catalog SC-01–SC-53 (v0.1.0 gates) | fixtures M1–M11; executed M14 |
| **PRD 18** | Issuance integrity (identity chain, pipeline, replay, revoke-vs-inflight) | M2, M4, M6, M9 |
| **PRD 19** | Harness compatibility (honest labels) | M10, M14 (runs), M15 (matrix) |
| **PRD 20** | Standards & claims (RFC conformance, claim labels, MCP contribution) | M4, M11, M15 |
| **PRD 21** | Evidence register & method (context-dump + kill-time protocols) | M11 (scanner), M14 (study), M15 |
| **PRD 22** | Operations & governance (runbooks, drills) | M12 (tooling), M13 (runbooks), M14 (drills) |
| **PRD 23** | Enterprise adoption (honest gaps) | M15 (claims, no over-claim) |
| **Appendix A** | Consolidated source PRD (verbatim) | reference; trace maintained |

## Requirements → milestone (v0.1.0: R1–R9 + R17, E1–E15)

| Req | Milestone | Req | Milestone |
|---|---|---|---|
| R1 reference-only context | M2, M8 | E1 contract + idempotent resolution | M2 |
| R2 egress injection at use | M4, M5 | E2 durable store + recovery | M1 |
| R3 token bindings (audience/tool/session) | M2, M4 | E3 unforgeable single-use issuance | M2, M6 |
| R4 revoke ≤1s | **M6** | E4 fail-closed everywhere | M3, M9 |
| R5 keychain + file backends | M3 | E5 redaction-by-default + receipts | M3, M11 |
| R6 lifecycle events + ledger | M7 | E6 time correctness | M6 |
| R7 secret-evasion detection | M9 | E7 egress-injection engine | M4, M5 |
| R8 **stdio MCP virtualization** | **M5** | E8 harness adapters (≥2 Tier-1) | M10 |
| R9 step-up issuance | M10 | E9 pluggable backends (conformance-gated) | M3 |
| R17 scan + migrate | M8 | E10 outside-the-agent control plane / tamper | M9 |
| | | E11 versioning + compatibility | M1, M2 |
| | | E12 ledger + export/verify-log | M7 |
| | | E13 standards conformance gate | M4, M11 |
| | | E14 no token passthrough; audience at egress | M4, M5 |
| | | E15 supply-chain integrity | M11, M15 |

**Forward slate (P1/P2 — out of v0.1.0 scope):** R10 (enterprise/cloud backends), R11 (server/HA/fleet),
R12 (SPIFFE/WIMSE identity), R18 (posture), R13 (budgets), R14 (DPoP), R15 (MCP attestation), R16 (egress
taint), R19 (canaries). Their WBS is written at v0.1.x ([PRD 09](../../prd/09-roadmap.md)).

## CUJ → milestone (CUJ-1..14)

| CUJ | Journey (short) | Milestone |
|---|---|---|
| **CUJ-1** | First brokered credential in 15 minutes (scan → migrate → brokered call) | **M8** (end-to-end: scan/migrate → store → backend → egress) |
| **CUJ-2** | Revoke in one second under fire (the spine) | **M6** |
| **CUJ-3** | Context-dump finds zero credentials (the invariant) | **M2** (+M11 scanner gate) |
| **CUJ-4** | stdio MCP auth with no secret in env/config/context | **M5** |
| **CUJ-5** | Token binding proven: replay elsewhere fails | **M4** (+M2 bindings) |
| **CUJ-6** | Secret-evasion caught | **M9** |
| **CUJ-7** | Step-up JIT issuance for a prod credential | **M10** |
| **CUJ-8** | Backend fail-closed day | **M3** |
| **CUJ-9** | Credential-lifecycle audit reconstruction | **M7** |
| **CUJ-10** | Rotate a backend secret without restarting the agent | **M3** (references re-resolve) |
| **CUJ-11** | Air-gapped / offline day | **M11** (verified offline) |
| **CUJ-12** | Two harnesses, one broker | **M10** |
| **CUJ-13** | Embed the broker in a product | **M2** (SDK/CLI contract) + M10 |
| **CUJ-14** | Enterprise reviewer honesty | **M15** (claims lint + gap docs) |

> Every CUJ appears in exactly one milestone's **CUJ** column in its part file. No CUJ is orphaned; no
> milestone claims a CUJ it does not deliver.

## Scenario → milestone (SC-01..SC-53, [PRD 17](../../prd/17-scenarios.md))

| Scenario | What it proves | Authored / gated at | Executed |
|---|---|---|---|
| **SC-01** | First brokered call < 15 min, no code change | M8 (scan/migrate + egress wired) | **M14** |
| **SC-02** | Env-injection end-to-end | M4 | **M14** |
| **SC-03** | Header-injection end-to-end | M4 | **M14** |
| **SC-04** | RFC 8693 exchange end-to-end | M4 | **M14** |
| **SC-05** | TTL expiry fires exactly once | M6 | **M14** |
| **SC-06** | Rotate without restart | M3 | **M14** |
| **SC-07** | Two harnesses, one broker | M10 | **M14** |
| **SC-08** | Audience replay fails | M2 + M4 | **M14** |
| **SC-09** | Tool-scope replay fails | M2 + M4 | **M14** |
| **SC-10** | Session-bound replay fails | M2 + M4 | **M14** |
| **SC-11** | Stale / forwarded / widened issuance fails | M2 + M4 | **M14** |
| **SC-12** | stdio authenticates with no secret in config/env/context | M5 | **M14** |
| **SC-13** | stdio: no token passthrough | M5 | **M14** |
| **SC-14** | `.env` read attempt caught | M9 | **M14** |
| **SC-15** | Cloud credential file read caught | M9 | **M14** |
| **SC-16** | Keychain read outside the broker caught | M9 | **M14** |
| **SC-17** | Enforce-mode block + honest gap | M9 | **M14** |
| **SC-18** | Locked backend → deny | M3 | **M14** |
| **SC-19** | Absent backend → deny | M3 | **M14** |
| **SC-20** | Ambiguous / partial config → deny | M3 | **M14** |
| **SC-21** | Corrupt store → no new issuance | M1 | **M14** |
| **SC-22** | Sink offline → local ledger authoritative | M7 | **M14** |
| **SC-23** | `kill -9` mid-issue → recover + exactly-once | M1 | **M14** |
| **SC-24** | **Kill-time ≤1s (release-blocking)** | **M6** | **M14** |
| **SC-25** | Scoped revoke does not over-kill | M6 | **M14** |
| **SC-26** | Revoke during an in-flight call | M6 | **M14** |
| **SC-27** | Revoke unknown target → error, not silence | M6 | **M14** |
| **SC-28** | `revoked` event carries operator identity | M6 | **M14** |
| **SC-29** | `export --session` reconstructs the lifecycle | M7 | **M14** |
| **SC-30** | Ledger tamper detected | M7 | **M14** |
| **SC-31** | Export contains no secret material | M11 | **M14** |
| **SC-32** | agentwatch event per transition | M7 | **M14** |
| **SC-33** | Step-up approved | M10 | **M14** |
| **SC-34** | Step-up denied / timeout → no credential | M10 | **M14** |
| **SC-35** | Tier-1 recipe A ends in an authenticated call | M10 | **M14** |
| **SC-36** | Tier-1 recipe B ends in an authenticated call | M10 | **M14** |
| **SC-37** | Generic MCP client / custom SDK path | M10 | **M14** |
| **SC-38** | Honest "not yet" for an uncovered harness | M10 | **M14** |
| **SC-39** | Air-gapped day | M11 | **M14** |
| **SC-40** | **Context-dump finds 0 usable creds (release-blocking)** | **M2** (+M11) | **M14** |
| **SC-41** | **Tamper against us fails closed (release-blocking)** | M9 | **M14** |
| **SC-42** | Injector scope-widening rejected | M4 | **M14** |
| **SC-43** | **Evidence scanner: 0 secrets (release-blocking)** | M11 | **M14** |
| **SC-51** | Scan/migrate: 100% recall, 0 printed, finding closed **(P0)** | **M8** | **M14** |
| **SC-44** | Enterprise/cloud backends resolve (R10, P1) | — (forward slate) | v0.1.x WBS |
| **SC-45** | Server/HA fleet broker; monotonic delegation (R11, P1) | — | v0.1.x WBS |
| **SC-46** | SPIFFE/WIMSE SVID as actor token (R12, P1) | — | v0.1.x WBS |
| **SC-47** | Blast-radius budgets exhaust → halt (R13, P2) | — | v0.3.0 WBS |
| **SC-48** | DPoP proof-of-possession (R14, P2) | — | v0.3.0 WBS |
| **SC-49** | MCP attestation/reputation feed (R15, P2) | — | v0.3.0 WBS |
| **SC-50** | Egress taint/DLP (R16, P2) | — | v0.3.0 WBS |
| **SC-52** | Credential posture report (R18, P1) | — | v0.1.x WBS |
| **SC-53** | Canary reference fires on use (R19, P2) | — | v0.3.0 WBS |

**Release gating at M14:** SC-24 (kill-time), SC-40 (context-dump), SC-41 (tamper fail-closed), SC-43
(no-secret scanner), and SC-51 (scan/migrate) are release-blocking — a red verdict blocks M15.

## Decisions (PRD 11)

D-01 (broker, never vault) → M3 · D-02 (never mint long-lived) → M2/M4 · D-03 (below the harness) → M4/M10 ·
D-04 (references opaque + loggable) → M2 · D-05 (egress injection, three drivers) → M4 · D-06 (fail closed)
→ M3/M9 · D-07 (revoke explicit + unconditional) → M6 · D-08 (SQLite single-writer) → M1 · D-09 (hash-chained
ledger) → M7 · D-10 (step-up via agentpolicy) → M10 · D-11 (stdio process boundary) → M5 · D-12 (local-first)
→ M0/M11 · D-13 (additive contracts) → M1/M2 · D-14 (no token passthrough) → M4/M5 · D-15 (DPoP deferred)
→ out of scope (R14) · D-16 (enterprise backends deferred) → out of scope (R10) · D-17 (shared-session rules)
→ M4 (session binding) + R11 later.

## v0.1.0 release gate (all milestones)

- [ ] M0–M13 exit criteria satisfied (design docs first, tests, coverage ≥95%, ruff/mypy, review, docs)
- [ ] Every R1–R9 + R17 and E1–E15 demonstrated by its acceptance test ([PRD 12](../../prd/12-traceability.md) rows green)
- [ ] **Kill-time ≤1s** end-to-end (issue → revoke → replay fails), running **in CI**; re-run at M14
- [ ] **Context-dump finds 0 usable credentials** across every variant (permanent invariant)
- [ ] No path from any failure to a credential (fail-closed fault matrix 100% deny-or-pending)
- [ ] **stdio MCP virtualization** proven (SC-12/SC-13) with the documented process-boundary limit
- [ ] **scan/migrate** 100% recall on the seeded fixture, 0 printed secrets (SC-51)
- [ ] SC-01–SC-53 executed with the honest report published (M14); attack packs green
- [ ] Install → first brokered call < 15 minutes on the field-test box (CUJ-1)
- [ ] Full lifecycle works with **no network** (CUJ-11); the standards conformance report is green (E13)
- [ ] Compatibility matrix published with honest labels only (M15)
- [ ] **Security audit green (M15): `trufflehog` finds no live credential in the tree, and a full
      git-history scan finds no token leak in any past commit** — a finding blocks the tag
- [ ] SBOM + signed artifacts (SLSA/Sigstore); OpenSSF Scorecard recorded; claims lint green vs the
      [PRD 20 §6](../../prd/20-standards-and-claims.md) vocabulary

Review log: [codereview-log.md](codereview-log.md).
