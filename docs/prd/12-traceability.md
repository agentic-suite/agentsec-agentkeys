# PRD 12 — Traceability

**BLUF:** This is the spine that ties the PRD set to the build and the evidence: every requirement maps to
**the user story it serves → the CUJ that exercises it → the field-test scenario that measures it → the test
file that gates it in CI**. Two coverage classes are traced — the **P0 product requirements R1–R9** and the
**P0 engineering requirements E1–E15** — and every one of them lands on at least one scenario id
(SC-01…SC-43). The forward slate (**R10–R16**, P1/P2) is traced to *planned* scenario ids (SC-44…SC-50) and
is **labeled as not yet built**, not quietly dropped. The rule the matrix enforces is simple: **no P0
requirement may be unmapped**, and no cell may claim a higher confidence than its evidence (see
[PRD 20 §6](20-standards-and-claims.md), [PRD 21](21-evidence-register-and-method.md)).

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## How to read this matrix

- **Req** — the requirement id from [PRD 05](05-features.md) (`R#` product, `E#` engineering).
- **Story** — the user story id from [PRD 04 §2](04-users-and-cujs.md) (`US-##`).
- **CUJ** — the critical user journey from [PRD 04 §3](04-users-and-cujs.md) (`CUJ-#`).
- **Scenario** — the field-test scenario id from [PRD 17](17-scenarios.md) (`SC-##`). The scenario is the
  *end-to-end* evidence; the test file is the *unit/contract* evidence.
- **Test file** — the CI test that gates the requirement. Names follow the feature doc
  ([PRD 05](05-features.md)); `tests/conformance/*` are the standards gate (E13).
- **Groups:** P0 (v0.1.0) first, then P1 (v0.1.x–v0.2.0), then P2 (v0.3.0+). A scenario id is unique across
  releases so both this matrix and [PRD 17](17-scenarios.md) resolve to the same case.
- **Status:** *P0* rows are the build of record; *P1/P2* rows are **planned — not yet built**. Test-file
  names for planned rows are the intended paths, not existing files.

---

## 0. v0.1.0 — foundation (M0, built 2026-11-09)

M0 carries no R-scenario of its own; it lands the first slice of **E4** (fail-closed config) and **E15**
(the CI quality gate) and freezes the contracts every later row depends on.

| Work item | What it lands | Test file |
|---|---|---|
| `0.D0` design | Foundation design of record (CLI surface, exit codes, config, store sketch) | `docs/design/v0.1.0/foundation.md` |
| `0.1` packaging | `agentsec-agentkeys` dist, `agentkeys` package + console script (`E15`) | `tests/test_packaging.py` |
| `0.2` CLI surface | the frozen v0.1.0 command surface + honest stubs | `tests/test_cli.py` |
| `0.3` exit codes | reserved exit-code contract `0/1/2/3/4` | `tests/test_exit_codes.py` |
| `0.4` config | references-only TOML model, fail-closed (`E4`) + branch coverage | `tests/test_config.py`, `tests/test_config_gate.py` |
| `0.5` CI | `ruff` + `mypy --strict` + tests + coverage ≥95% + DCO (`E15`) | `tests/test_ci_workflow.py` |
| `0.6` `doctor` | read-only health checks, exit-coded | `tests/test_doctor.py` |
| `0.7` identity | README/LICENSE/CODEOWNERS/SECURITY/AGENTS/CONTRIBUTING | `tests/test_identity_docs.py` |

## 0.1 v0.1.0 — store (M1, built 2026-11-09)

The BrokerStore contract and its two drivers. Lands the first real slice of **E2** (durable store) and
**E11** (versioning), and the foundation **E12**'s ledger will build on.

| Work item | What it lands | Test file |
|---|---|---|
| `1.D0` design | BrokerStore contract, six semantics, DDL, capability selection | `docs/design/v0.1.0/store.md` |
| `1.1` contract | typed records, `CapabilityFlags`, chain hashing, errors | `tests/test_store_contract.py` |
| `1.2` SQLite driver | WAL, fsync'd commits, `0700`/`0600`, indexes, atomic issue, CAS revoke | `tests/test_store_sqlite.py` |
| `1.3` memory driver | identical semantics, ephemeral | `tests/test_store_memory.py` |
| `1.4` conformance suite | S1-S6 as fixtures; four broken fakes must fail it | `tests/test_store_conformance.py`, `tests/store_conformance.py` |
| `1.5` migrations | forward-only, loud downgrade refusal, corrupt-store refusal | `tests/test_store_migrations.py` |
| `1.6` loader | `agentkeys.store` entry points, admission, capability refusal | `tests/test_store_loader.py` |
| `1.T` recovery | crash mid-issue → all-or-none, retry exactly once | `tests/test_store_recovery.py` |

## 0.2 v0.1.0 — contracts + resolution (M2, built 2026-11-09)

Lands the first slice of **E1** (contract + idempotent resolution), **E3** (single-use issuance), and
**R1/R3** (references only; audience/tool/session bindings).

| Work item | What it lands | Test file |
|---|---|---|
| `2.D0` design | contracts design of record (identity chain, pipeline order) | `docs/design/v0.1.0/contracts.md` |
| `2.1` `akref/1.0` | reference model + strict key grammar; opaque + loggable | `tests/test_reference_contract.py` |
| `2.2` `issuance/1.0` | binding triple; TTL within class window; no plaintext field | `tests/test_issuance_contract.py` |
| `2.3` registry | register/list; unknown key refused loudly | `tests/test_registry.py` |
| `2.4` idempotent resolution | retry returns the same issuance, mints nothing (`E1`) | `tests/test_resolution.py` |
| `2.5` single-use secret | hashed token, typed consume, replay rejected (`E3`) | `tests/test_resolution.py` |
| `2.6` SDK / CLI | embedder surface + `ref list|show`; no `get_secret()` | `tests/test_sdk_cli_contract.py` |

## 0.3 v0.1.0 — backends + fail-closed engine + redactor (M3, built 2026-11-09)

Lands the first slice of **R5** (keychain + file backends), **E4** (fail closed), **E9** (pluggable
backends), and **E5** (redaction by default + receipts).

| Work item | What it lands | Test file |
|---|---|---|
| `3.D0` design | backend contract, drivers, fault matrix, redaction vocabulary | `docs/design/v0.1.0/backends.md` |
| `3.1` contract | opaque `SecretValue`, capabilities, health, denial vocabulary | `tests/test_backend_contract.py` |
| `3.2` keychain driver | unlock-per-resolve; no caching; no disk write | `tests/test_backend_keychain.py` |
| `3.3` file driver | `0600` at open and resolve; rotation without restart | `tests/test_backend_file.py` |
| `3.4` conformance suite | one suite for every backend; broken drivers must fail | `tests/test_backends_conformance.py` |
| `3.5` fail-closed engine | every failure → a structured denial; no fallback | `tests/test_failclosed_matrix.py` |
| `3.6` redactor + receipts | mask before persist/render/export; a receipt per field | `tests/test_redactor_receipts.py` |

## 0.4 v0.1.0 — egress-injection engine (M4, built 2026-11-09)

Lands the first slice of **R2/R3** (egress injection; bindings), **E7** (the injection engine),
**E14** (no passthrough), and **E13** (RFC 8693 conformance at the driver level).

| Work item | What it lands | Test file |
|---|---|---|
| `4.D0` design | one interface, three drivers, the four rules, denials | `docs/design/v0.1.0/egress.md` |
| `4.1` interface + rules | binding is the ceiling; forget; typed denials; rejection events | `tests/test_inject_contract.py` |
| `4.2` env driver | child environment only; parent untouched | `tests/test_inject_env.py` |
| `4.3` header driver | overwrite client credential headers | `tests/test_inject_header.py` |
| `4.4` RFC 8693 driver | narrow audience/scope; broker subject; `act` | `tests/test_inject_exchange.py` |
| `4.5` audience enforcement | SC-08-SC-11 + SC-42 deny and log | `tests/test_binding_audience.py` |
| `4.6` session binding | one agent per session (D-17) | `tests/test_binding_session.py` |

## 0.5 v0.1.0 — stdio MCP credential virtualization (M5, built 2026-11-09)

Lands the flagship: **R8** (stdio virtualization), with **E7** (the injection engine) and **E14** (no
passthrough) applied to the stdio case.

| Work item | What it lands | Test file |
|---|---|---|
| `5.D0` design | wrapper, proxy, substitution, the honest boundary limit | `docs/design/v0.1.0/stdio.md` |
| `5.1` launch wrapper | `agentkeys run --server` builds the child env and proxies stdio | `tests/test_stdio_cli_run.py`, `tests/test_stdio_virtualization.py` |
| `5.2` stdio proxy | byte-for-byte frames, stderr-only logging, frame cap | `tests/test_stdio_proxy.py` |
| `5.3` substitution | placeholder → scoped token, with receipts | `tests/test_stdio_virtualization.py` |
| `5.4` no passthrough | client credential stripped; server receives a broker token | `tests/test_stdio_no_token_passthrough.py` |
| `5.5` pattern + ext-auth | the placeholder pattern documented; fixtures + appendix staged | `docs/reference/stdio-virtualization.md`, `docs/design/v0.1.0/stdio-ext-auth-appendix.md` |

## 1. v0.1.0 — P0 product requirements (R1–R9 + R17)

> **Implemented (M6–M10, 2026-11-09).** R4, R6, R7, R9, R17 and E6, E8, E10, E12 are implemented and
> covered by the test files listed below. A row is *green* only with the milestone gate recorded in the
> [WBS Progress](../wbs/v0.1.0/wbs-v0.1.0-index.md#progress); the field-test verdicts remain M14's.

| Req | Story | CUJ | Scenario | Test file |
|---|---|---|---|---|
| **R1** Reference-only context | US-01 | CUJ-1, CUJ-3, CUJ-10 | SC-01, SC-06, SC-40, SC-43 | `tests/test_reference_leak.py`, `tests/test_reference_grammar.py` |
| **R2** Egress injection at use | US-02 | CUJ-1, CUJ-4, CUJ-12 | SC-02, SC-03, SC-04, SC-12, SC-35, SC-36, SC-37 | `tests/test_inject_env.py`, `tests/test_inject_header.py`, `tests/test_inject_exchange.py` |
| **R3** Token bindings | US-03 | CUJ-5 | SC-08, SC-09, SC-10, SC-11 | `tests/test_binding_audience.py`, `tests/test_binding_tool.py`, `tests/test_binding_session.py` |
| **R4** Revoke ≤1s | US-04, US-13, US-14, US-15 | CUJ-2 | SC-24, SC-25, SC-26, SC-27, SC-28 | `tests/test_revoke_killtime.py`, `tests/test_revoke_scope.py` |
| **R5** Keychain + file backends, fail-closed | US-06, US-12 | CUJ-8, CUJ-11 | SC-18, SC-19, SC-20, SC-39 | `tests/test_backend_keychain.py`, `tests/test_backend_file.py`, `tests/test_failclosed_matrix.py` |
| **R6** Lifecycle events + ledger | US-07, US-19, US-20, US-21 | CUJ-9 | SC-29, SC-30, SC-32 | `tests/test_ledger_chain.py`, `tests/test_export.py` |
| **R7** Secret-evasion detection | US-08 | CUJ-6 | SC-14, SC-15, SC-16, SC-17 | `tests/test_evasion_detect.py`, `tests/test_evasion_enforce.py` |
| **R8** stdio MCP virtualization (flagship) | US-16, US-17, US-18 | CUJ-4 | SC-12, SC-13 | `tests/test_stdio_virtualization.py`, `tests/test_stdio_no_token_passthrough.py` |
| **R9** Step-up issuance | US-09 | CUJ-7 | SC-33, SC-34 | `tests/test_stepup_approved.py`, `tests/test_stepup_denied.py` |
| **R17** Secret-hygiene scan + migration | US-27 | CUJ-1 | SC-51 | `tests/test_scan_candidates.py`, `tests/test_migrate_flow.py` |

## 2. v0.1.0 — P0 engineering requirements (E1–E15)

| Req | Story | CUJ | Scenario | Test file |
|---|---|---|---|---|
| **E1** Reference + issuance contract, idempotent | US-22 | CUJ-13 | SC-01, SC-37 | `tests/test_contract.py`, `tests/test_idempotency.py` |
| **E2** Durable broker store, capability-gated | US-10, US-22 | CUJ-13 | SC-21, SC-23 | `tests/test_store_capabilities.py`, `tests/test_store_recovery.py` |
| **E3** Unforgeable, single-use, session-bound issuance | US-03 | CUJ-5 | SC-11, SC-23, SC-33 | `tests/test_issuance_single_use.py`, `tests/test_binding_session.py` |
| **E4** Fail-closed degradation, everywhere | US-10 | CUJ-8 | SC-18, SC-19, SC-20, SC-21, SC-22 | `tests/test_failclosed_matrix.py` |
| **E5** Redaction-by-default + receipts | US-01, US-07 | CUJ-3 | SC-31, SC-43 | `tests/test_redactor_receipts.py`, `tests/test_evidence_scan.py` |
| **E6** Time correctness | US-14 | CUJ-2 | SC-05 | `tests/test_time_correctness.py` |
| **E7** Transport-agnostic egress-injection engine | US-02 | CUJ-1, CUJ-4 | SC-02, SC-03, SC-04, SC-11, SC-42 | `tests/test_inject_env.py`, `tests/test_inject_header.py`, `tests/test_inject_exchange.py` |
| **E8** Harness adapters (≥2 Tier-1) | US-24 | CUJ-12 | SC-35, SC-36, SC-38 | `tests/test_harness_recipe_claude_code.py`, `tests/test_harness_recipe_cursor.py` |
| **E9** Pluggable backends, conformance-gated | US-23 | CUJ-13 | SC-44 *(P1)* | `tests/test_backend_conformance.py` |
| **E10** Outside-the-agent control plane | US-10 | CUJ-6 | SC-17, SC-41, SC-42 | `tests/test_tamper_config.py`, `tests/test_tamper_broker.py` |
| **E11** Versioning + compatibility | US-22 | CUJ-13 | SC-23 | `tests/test_schema_migration.py`, `tests/test_contract_compat.py` |
| **E12** Ledger + chain + export + agentwatch sink | US-07, US-19, US-20 | CUJ-9 | SC-22, SC-29, SC-30, SC-32 | `tests/test_ledger_chain.py`, `tests/test_export.py` |
| **E13** Standards conformance gate | all | CUJ-14 | SC-08, SC-33 | `tests/conformance/test_rfc8693.py`, `test_rfc8707.py`, `test_rfc9700.py`, `test_rfc9728.py`, `test_rfc9068.py`, `test_pkce.py`, `test_mcp_auth.py`, `test_otel_semconv.py` |
| **E14** No token passthrough | US-18 | CUJ-4 | SC-13 | `tests/test_no_token_passthrough.py`, `tests/conformance/test_no_token_passthrough.py` |
| **E15** Supply-chain integrity | all | — | release gate | `tests/test_supply_chain.py` (attestations/SBOM/Scorecard gate) |

## 3. P1 — v0.1.x–v0.2.0 (planned — not yet built)

| Req | Story | CUJ | Scenario | Test file (planned) |
|---|---|---|---|---|
| **R10** Enterprise/cloud backends | US-23 | CUJ-13 | SC-44 *(planned)* | `tests/test_backend_onepassword.py`, `tests/test_backend_vault.py` |
| **R11** Server / HA / fleet mode | US-24 | CUJ-12 | SC-45 *(planned)* | `tests/test_server_mode.py` |
| **R12** SPIFFE/WIMSE workload identity | US-24 | CUJ-12 | SC-46 *(planned)* | `tests/test_identity_spiffe.py` |
| **R18** Credential posture report | US-28 | CUJ-8 | SC-52 *(planned v0.1.x)* | `tests/test_posture_report.py` |

## 4. P2 — v0.3.0+ (planned — not yet built)

| Req | Story | CUJ | Scenario | Test file (planned) |
|---|---|---|---|---|
| **R13** Blast-radius budgets | — | — | SC-47 *(planned)* | `tests/test_blast_radius_budget.py` |
| **R14** DPoP sender-constrained tokens | — | — | SC-48 *(planned)* | `tests/conformance/test_dpop.py` |
| **R15** MCP attestation/reputation feed | — | — | SC-49 *(planned)* | `tests/test_mcp_attestation_feed.py` |
| **R16** Egress taint / DLP | — | — | SC-50 *(planned)* | `tests/test_egress_taint.py` |
| **R19** Canary references | — | CUJ-6 | SC-53 *(planned)* | `tests/test_canary_references.py` |

## 5. Requirement → priority → release summary

| Req | Pri | Release | Req | Pri | Release |
|---|---|---|---|---|---|
| R1–R9, R17 | P0 | v0.1.0 | E1–E15 | P0 | v0.1.0 |
| R10–R12, R18 | P1 | v0.1.x–v0.2.0 | — | — | — |
| R13–R16, R19 | P2 | v0.3.0+ | — | — | — |

## 6. Coverage gaps & honesty notes

- **Nothing P0 is unmapped.** Every `R#` (R1–R9) and every `E#` (E1–E15) in §1–§2 resolves to at least one
  scenario id and at least one test file. This is a *design* claim: the matrix is complete, not the code.
- **Planned ≠ present.** P1/P2 rows and their test paths are **not yet written**. They are named here so the
  trace is continuous when the work lands, and they are labeled *planned* wherever they appear.
- **E9's first live scenario is P1.** E9 (pluggable backends) is P0 for *architecture*, but its cross-vendor
  proof (SC-44) arrives with **R10**, so §2 points E9 at a P1 scenario deliberately — an honest forward
  reference, not a missing P0 gate. The v0.1.0 gate for E9 is the backend **conformance suite**, which runs
  against keychain/file.
- **E15 has no scenario id.** Supply-chain integrity is a **release gate** (signed artifacts, SLSA
  provenance, SBOM, Scorecard, OSS-Fuzz), not a field-test journey; it maps to `tests/test_supply_chain.py`
  and the release checklist, and is listed under *verified* rather than *field-tested* only after a third
  party reproduces a release.
- **Conformance vs field-test.** `tests/conformance/*` prove spec compliance (label *conformance*); the
  SC-xx scenarios produce the *field-tested* evidence recorded in the hand-maintained report
  ([PRD 21](21-evidence-register-and-method.md)). A green unit test is **not** a field-test pass.
- **No scenario claims evidence we have.** Every SC id in this matrix is a **planned** case until the
  hand-maintained field-test report records its verdict; today the whole set is *documented*.

## 7. Scenario id index (P0 — see [PRD 17](17-scenarios.md))

| Pack | Scenario ids | Requirements |
|---|---|---|
| Core lifecycle (CL) | SC-01…SC-07 | R1, R2, R5, E1, E6, E7 |
| Binding / replay (BR) | SC-08…SC-11 | R3, E3, E7 |
| stdio MCP (ST) | SC-12…SC-13 | R8, E7, E14 |
| Evasion (EV) | SC-14…SC-17 | R7, E10 |
| Fail-closed / fault-injection (FC) | SC-18…SC-23 | R5, E2, E4, E12 |
| Revocation / kill-time (RK) | SC-24…SC-28 | R4, E3, E6, E12 |
| Lifecycle-audit (LA) | SC-29…SC-32 | R6, E5, E12 |
| Step-up (SU) | SC-33…SC-34 | R9, E3 |
| Harness-compat (HC) | SC-35…SC-38 | E8, E1 |
| Air-gapped (AG) | SC-39 | R5, E4, E12 |
| Attack packs (AP) | SC-40…SC-43 | R1, E5, E7, E10 |
| Migration & posture (MP) | SC-51…SC-52 | R17, R18 |
| Forward slate *(planned)* | SC-44…SC-50, SC-53 | R10–R16, R19 |

## 8. Test-file index (CI gates)

| Test family | Gates | Requirement |
|---|---|---|
| `tests/test_reference_leak.py`, `test_reference_grammar.py` | reference safety + grammar | R1, E1 |
| `tests/test_contract.py`, `test_idempotency.py`, `test_contract_compat.py` | contract + idempotent ops | E1, E11 |
| `tests/test_inject_env.py`, `test_inject_header.py`, `test_inject_exchange.py` | three egress drivers | R2, E7 |
| `tests/test_binding_audience.py`, `test_binding_tool.py`, `test_binding_session.py`, `test_issuance_single_use.py` | bindings + single-use | R3, E3 |
| `tests/test_revoke_killtime.py`, `test_revoke_scope.py`, `test_revoke_cli.py` | kill-time + scoped kill + replay proof | R4, E6 |
| `tests/test_events.py`, `test_correlation.py`, `test_sink.py` | event set, join keys, sink gap marker | R6, E12 |
| `tests/test_backend_keychain.py`, `test_backend_file.py`, `test_backend_conformance.py`, `test_failclosed_matrix.py` | backends + fail-closed | R5, E4, E9 |
| `tests/test_store_capabilities.py`, `test_store_recovery.py`, `test_schema_migration.py` | durable store + recovery | E2, E3, E11 |
| `tests/test_ledger_chain.py`, `test_export.py` | ledger chain + export | R6, E12 |
| `tests/test_redactor_receipts.py`, `test_evidence_scan.py` | redaction + no-secret scan | E5 |
| `tests/test_evasion_detect.py`, `test_evasion_enforce.py` | evasion detect + enforce | R7, E10 |
| `tests/test_stdio_virtualization.py`, `test_stdio_no_token_passthrough.py` | stdio virtualization | R8, E14 |
| `tests/test_stepup_approved.py`, `test_stepup_denied.py` | step-up gating | R9 |
| `tests/test_harness_recipe_claude_code.py`, `test_harness_recipe_cursor.py`, `test_recipe_acceptance.py` | ≥2 Tier-1 recipes + acceptance harness | E8 |
| `tests/test_tamper_config.py`, `test_tamper_broker.py` | tamper resistance | E10 |
| `tests/test_no_token_passthrough.py` | no passthrough (unit) | E14 |
| `tests/test_supply_chain.py` | release supply-chain gate | E15 |
| `tests/test_scan_candidates.py`, `test_migrate_flow.py`, `test_scan_cli.py`, `test_posture_report.py` | migration + posture | R17, R18 |
| `tests/conformance/test_rfc8693.py` … `test_otel_semconv.py` | standards conformance | E13, E14 |

## 9. Related documents

- Requirements, priorities, and the F-catalog: [PRD 05](05-features.md).
- Stories, personas, and CUJ definitions: [PRD 04](04-users-and-cujs.md).
- The scenario catalog, packs, and scoring: [PRD 17](17-scenarios.md).
- The frozen decisions behind the requirements: [PRD 11](11-decisions.md).
- Evidence register and the label vocabulary: [PRD 21](21-evidence-register-and-method.md),
  [PRD 20 §6](20-standards-and-claims.md).
