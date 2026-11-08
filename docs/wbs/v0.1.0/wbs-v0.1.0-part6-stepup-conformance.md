# WBS v0.1.0 — Part 6: Approvals & Assurance (M10–M11)

**BLUF:** **M10 ships step-up issuance** — prod-class scope becomes impossible to mint without an approving
human decision via agentpolicy, timeout = deny ([R9](../../prd/05-features.md)) — and the first **harness
recipes** (Claude Code, Cursor, generic) that end in a verified authenticated call
([E8](../../prd/05-features.md)). **M11 closes the assurance gap**: the **conformance kit** (RFC 8693 / 8707 /
9700 / 9728 / 9068 / 7636, no-passthrough, backend drivers — [E13](../../prd/05-features.md)), the **security
hardening sweep** with the evidence scanner and attack packs, and the **supply-chain floor**
([E15](../../prd/05-features.md)).

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M10 — Step-up issuance + harness recipes (R9, E8)

**Goal:** a higher-class mint requires an approving decision the broker records (`provenance` /
`authorization.source`), and the same broker serves **≥2 Tier-1 harnesses** through thin recipes — the
below-the-harness claim made concrete ([PRD 19](../../prd/19-harness-compatibility.md),
[PRD 16 §2](../../prd/16-adapters-and-integration.md)).

**CUJ:** [CUJ-7](../../prd/04-users-and-cujs.md) (step-up), [CUJ-12](../../prd/04-users-and-cujs.md)
(two harnesses) · **Requirements:** [R9](../../prd/05-features.md), [E8](../../prd/05-features.md),
[E3](../../prd/05-features.md), [PRD 18 §5](../../prd/18-issuance-integrity.md),
[PRD 19](../../prd/19-harness-compatibility.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 10.D0 | **Design docs first** | Step-up flow + provenance fields; recipe format; the Tier-1 order (Claude Code first) | docs | reviewed before code | #124 | — | — |
| 10.1 | agentpolicy client (ask) | Ask for a decision; record `provenance.decided_by` + `authorization.source`; never decide policy ourselves | adapter | an approval is recorded; a free-text "approval" from the agent is rejected | #125 | [CUJ-7](../../prd/04-users-and-cujs.md) | [R9](../../prd/05-features.md), [E3](../../prd/05-features.md) |
| 10.2 | Step-up gate | Prod-class mint blocked until approved; **timeout = deny**; `step-up-denied` is a structured deny the agent can rescope | core module | no prod-scoped mint without an approving decision | #126 | [CUJ-7](../../prd/04-users-and-cujs.md) | [R9](../../prd/05-features.md) |
| 10.3 | Claude Code recipe | `.mcp.json`/`~/.claude.json` wiring: `command: agentkeys run --server …`, reference-form `env`; header egress for HTTP | recipe doc + smoke | a verified authenticated call; config changes only (no broker fork) | #127 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 10.4 | Cursor recipe | `.cursor/mcp.json` wiring via the same wrapper pattern | recipe doc + smoke | a verified authenticated call | #128 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 10.5 | Generic recipes | Any stdio MCP client; any HTTP API; any RFC 8693 target; plain CLI via `agentkeys run --` | recipe docs | each recipe ends in a verified authenticated call | #129 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 10.6 | Recipe acceptance harness | A harness that runs a recipe to an authenticated call; packs gate it (agentdrill) | test harness | SC-35/SC-36 pass; a missing/incomplete recipe fails | #130 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 10.T | Tests | Step-up approve/deny/timeout; recipe smoke; no-widening | tests | coverage ≥95% | #131 | — | — |
| 10.C | Coverage gate | ≥95% on step-up/recipe modules | coverage report | ≥95% | #132 | — | — |
| 10.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #133 | — | — |
| 10.CR | Code review | Findings resolved | review log | no open findings | #134 | — | — |
| 10.D | Docs | [PRD 16 §2](../../prd/16-adapters-and-integration.md); [PRD 19](../../prd/19-harness-compatibility.md); [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #135 | — | — |
| 10.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 10.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] No prod-scoped mint without an approving decision; timeout = deny ([SC-33/SC-34](../../prd/17-scenarios.md))
- [ ] ≥2 Tier-1 recipes end in a verified authenticated call ([SC-35–SC-38](../../prd/17-scenarios.md)); no broker fork

**Planned (opens at `10.D0`).** Design: [`docs/design/v0.1.0/stepup-recipes.md`](../../design/v0.1.0/) · Scenarios:
[SC-07](../../prd/17-scenarios.md), [SC-33–SC-38](../../prd/17-scenarios.md) · Tests:
`tests/test_stepup_approved.py`, `tests/test_stepup_denied.py`, `tests/test_harness_recipe_claude_code.py`,
`tests/test_harness_recipe_cursor.py`.

---

## Milestone M11 — Conformance kit + supply chain + security hardening (E13, E15)

**Goal:** the product is **provable** — spec conformance is a release gate, the evidence scanner proves
no secret material sits anywhere, the attack packs run as release-blocking regressions, and the repo's own
supply chain (signed releases, SLSA, SBOM, Scorecard) is demonstrably clean, because Plugin4Shell proved
agents are a supply-chain target.

**CUJ:** [CUJ-11](../../prd/04-users-and-cujs.md) (air-gapped), [CUJ-14](../../prd/04-users-and-cujs.md)
(honesty) · **Requirements:** [E13](../../prd/05-features.md), [E15](../../prd/05-features.md),
[E5](../../prd/05-features.md), [E4](../../prd/05-features.md), [PRD 20 §1/§5](../../prd/20-standards-and-claims.md),
[PRD 21 §2](../../prd/21-evidence-register-and-method.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 11.D0 | **Design docs first** | Conformance suites; supply-chain gates; the evidence scanner + attack-pack design | docs | reviewed before code | #136 | — | — |
| 11.1 | Conformance kit + `agentkeys conformance` | RFC 8693/8707/9700/9728/9068/7636 suites + backend drivers + no-passthrough; a conformance failure is a release blocker | CLI + suite | `agentkeys conformance` green; unsupported standards labeled | #137 | — | [E13](../../prd/05-features.md) |
| 11.2 | Evidence scanner | Scan store/export/ledger payloads for secret-shape material; a seeded leak fails; self-test in CI | scanner | 0 secrets found; receipts present on redacted fields ([SC-43](../../prd/17-scenarios.md)) | #138 | — | [E5](../../prd/05-features.md) |
| 11.3 | Invariant negative fixtures | I1–I10 each get a negative fixture that must fail the build | fixtures | each invariant has a red-when-violated test | #139 | — | [PRD 06 §1](../../prd/06-security-baseline.md) |
| 11.4 | Attack packs (release-blocking) | Context-dump, tamper-against-us, scope-widening, spoof/replay; run as a release gate | packs | a broken gate turns the pack red | #140 | — | [E4](../../prd/05-features.md) |
| 11.5 | Supply-chain floor | Signed releases (Sigstore), SLSA provenance, SBOM (CycloneDX), OpenSSF Scorecard, pinned deps, `security.txt`, OSS-Fuzz targets | release tooling | badges/attestations present; fuzz targets run in CI | #141 | — | [E15](../../prd/05-features.md) |
| 11.6 | Offline / air-gap verification | Prove the core + revoke paths run with the network disabled; unsupported cloud backends warn and refuse | test | CUJ-11 offline day passes ([SC-39](../../prd/17-scenarios.md)) | #142 | [CUJ-11](../../prd/04-users-and-cujs.md) | [E4](../../prd/05-features.md) |
| 11.T | Tests | Conformance, scanner, invariants, packs, offline | tests | coverage ≥95% | #143 | — | — |
| 11.C | Coverage gate | ≥95% on conformance/security modules | coverage report | ≥95% | #144 | — | — |
| 11.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #145 | — | — |
| 11.CR | Code review | Findings resolved | review log | no open findings | #146 | — | — |
| 11.D | Docs | [PRD 20 §1/§5](../../prd/20-standards-and-claims.md); [PRD 21](../../prd/21-evidence-register-and-method.md); control-coverage matrix; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #147 | — | — |
| 11.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 11.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Conformance report green on the release commit ([E13](../../prd/05-features.md)); unsupported labeled
- [ ] Evidence scanner finds 0 secrets ([SC-43](../../prd/17-scenarios.md)); attack packs release-blocking
- [ ] Offline day passes ([SC-39](../../prd/17-scenarios.md)); supply-chain artifacts + Scorecard recorded

**Planned (opens at `11.D0`).** Design: [`docs/design/v0.1.0/conformance-supplychain.md`](../../design/v0.1.0/) ·
Scenarios: [SC-39](../../prd/17-scenarios.md), [SC-43](../../prd/17-scenarios.md) · Tests:
`tests/conformance/*`, `tests/test_evidence_scan.py`, `tests/test_supply_chain.py`.

---

Part 6 green ⇒ approvals are gated, recipes work, and the product is provable; proceed to
[Part 7 (M12–M13)](wbs-v0.1.0-part7-ops-docs.md).
