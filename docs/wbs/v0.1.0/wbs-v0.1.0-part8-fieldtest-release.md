# WBS v0.1.0 — Part 8: Field Test & Release (M14–M15) — FINAL

**BLUF:** The last two milestones, and the only ones that run on **real machines with real humans**.
**M14 is the field test** — the full SC-01–SC-53 catalog, the context-dump study, the harness runs, and the
published **kill-time benchmark**, with the report written **by hand** (automation never writes it,
[AGENTS.md](../../../AGENTS.md)). **M15 is release readiness** — the **security audit** (`trufflehog` + a
full **git-history scan for token leakage**), the claims lint, the compatibility matrix, the signed artifacts,
and the **`v0.1.0` tag**. A red field test or a security-audit finding blocks the tag.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M14 — Field tests — FINAL (SC-01–SC-53; study; benchmark)

**Goal:** prove the product on real hardware — a fresh install → first brokered call in <15 minutes, the
context-dump study on a real cohort, the harness recipes on the pinned versions, and a publicly re-runnable
kill-time benchmark. The **verdicts are entered by hand** from committed evidence; the report is
hand-maintained and carries the `HAND-MAINTAINED` marker ([PRD 21 §5](../../prd/21-evidence-register-and-method.md)).

**CUJ:** all ([CUJ-1–CUJ-13](../../prd/04-users-and-cujs.md)) · **Requirements:**
[R1](../../prd/05-features.md), [R4](../../prd/05-features.md), [R8](../../prd/05-features.md),
[R17](../../prd/05-features.md), [PRD 17](../../prd/17-scenarios.md), [PRD 21](../../prd/21-evidence-register-and-method.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 14.D0 | **Plan first** | `docs/field-test/v0.1.0/FIELD_TEST_PLAN.md`: the SC-01–SC-53 catalog, packs, scoring, the study protocol, the benchmark protocol | plan | reviewed before running | #172 | — | — |
| 14.1 | Field-test runner + case specs | The runner that executes each pack and writes raw results under `field-test/v0.1.0/results/` (never the report) | runner | results land under `results/`; the report is untouched | #173 | — | [PRD 21 §5](../../prd/21-evidence-register-and-method.md) |
| 14.2 | Core + binding packs | SC-01–SC-11: install→first call, env/header/exchange egress, bindings/replay | results | raw results committed | #174 | [CUJ-1](../../prd/04-users-and-cujs.md), [CUJ-5](../../prd/04-users-and-cujs.md) | [R2](../../prd/05-features.md), [R3](../../prd/05-features.md) |
| 14.3 | stdio + evasion + fail-closed packs | SC-12–SC-23: stdio virtualization, no-passthrough, evasion detect/enforce, fail-closed matrix | results | raw results committed | #175 | [CUJ-4](../../prd/04-users-and-cujs.md), [CUJ-6](../../prd/04-users-and-cujs.md), [CUJ-8](../../prd/04-users-and-cujs.md) | [R8](../../prd/05-features.md), [R7](../../prd/05-features.md), [E4](../../prd/05-features.md) |
| 14.4 | **Revoke / kill-time pack (release-blocking)** | SC-24–SC-28: end-to-end kill-time ≤1s, scoped revoke, in-flight, operator identity | results | p95 ≤1s **and** max ≤1s over N≥100; replay provably fails | #176 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 14.5 | **Context-dump study** | SC-40 + SC-43 on a real cohort: full context dump → **0 usable credentials**; the seeded falsification control must fire | study | 0 usable across every variant; a silent scanner is a FAIL | #177 | [CUJ-3](../../prd/04-users-and-cujs.md) | [R1](../../prd/05-features.md) |
| 14.6 | **Hand-maintained report** | `docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` with the `HAND-MAINTAINED` marker; verdicts entered by hand from committed results; the report-guard test asserts the refusal | report + guard test | no automation writes/rewrites the report; guard green | #178 | — | [PRD 21 §5](../../prd/21-evidence-register-and-method.md) |
| 14.7 | Harness recipe runs | SC-35–SC-38: ≥2 Tier-1 recipes end in a verified authenticated call on pinned versions | results | recipes verified; honest "not yet" for the rest | #179 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 14.8 | **Kill-time + context-dump benchmark (published)** | `bench/` reproducible pack; machine-readable JSON a third party can re-run | bench | published; a clean re-run reproduces the numbers | #180 | — | [PRD 07 §2](../../prd/07-success-metrics.md), [PRD 21 §6](../../prd/21-evidence-register-and-method.md) |
| 14.T | Tests | Pack runner + report guard | tests | coverage ≥95% | #181 | — | — |
| 14.C | Coverage gate | ≥95% on field-test tooling | coverage report | ≥95% | #182 | — | — |
| 14.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #183 | — | — |
| 14.CR | Code review | Findings resolved | review log | no open findings | #184 | — | — |
| 14.D | Docs | Field-test plan + report; [PRD 12](../../prd/12-traceability.md) rows; [PRD 17](../../prd/17-scenarios.md) verdicts | docs | docs updated + linked | #185 | — | — |
| 14.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 14.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Plan first · packs run · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] **SC-24 (kill-time), SC-40 (context-dump), SC-41 (tamper), SC-43 (no-secret scanner), SC-51 (scan/migrate) all PASS** — a red verdict blocks M15
- [ ] Install → first brokered call **<15 min** on the field box ([CUJ-1](../../prd/04-users-and-cujs.md))
- [ ] Report hand-maintained with the guard test green; benchmark published and re-runnable

**Planned (opens at `14.D0`).** Plan: [`docs/field-test/v0.1.0/FIELD_TEST_PLAN.md`](../../field-test/v0.1.0/) ·
Results: [`field-test/v0.1.0/results/`](../../../field-test/v0.1.0/) · Report:
[`docs/field-test/v0.1.0/FIELD_TEST_REPORT.md`](../../field-test/v0.1.0/) (hand-maintained).

---

## Milestone M15 — Release readiness — FINAL (security audit + tag `v0.1.0`)

**Goal:** everything a stranger needs to trust the release, and the release itself. The **security audit** is
the gate here: `trufflehog` must find no live credential in the tree, and a **full git-history scan must find
no token leak in any past commit**. Then claims lint, the compatibility matrix with honest labels, signed
artifacts, and the `v0.1.0` tag.

**CUJ:** [CUJ-14](../../prd/04-users-and-cujs.md) (enterprise honesty) · **Requirements:**
[R1](../../prd/05-features.md), [R4](../../prd/05-features.md), [E15](../../prd/05-features.md),
[PRD 06 §5](../../prd/06-security-baseline.md), [PRD 09 §3](../../prd/09-roadmap.md),
[PRD 20 §6–§7](../../prd/20-standards-and-claims.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 15.D0 | **Plan first** | Release plan: gate checklist, claims lint scope, audit scope, the tag/PyPI steps | plan | reviewed before tagging | #186 | — | — |
| 15.1 | **Security audit — secret leakage** | Run **`trufflehog`** across the working tree **and a full git-history scan** for token leakage (every commit, every branch); plus entropy/pattern scan of the store, exports, and fixtures; **any live credential in history blocks the tag** and is remediated (rotate + forward-fix, never a history rewrite) | audit report + CI gate | `trufflehog` finds 0 verified secrets in tree **and** history; a planted fake is caught (control) | #187 | — | [E15](../../prd/05-features.md), [PRD 06 §5](../../prd/06-security-baseline.md) |
| 15.2 | Claims lint | Lint every public claim against the [claims vocabulary](../../prd/20-standards-and-claims.md) — no claim above its evidence label | lint | lint green vs the vocabulary; gaps named, not smoothed | #188 | [CUJ-14](../../prd/04-users-and-cujs.md) | [PRD 20 §6](../../prd/20-standards-and-claims.md) |
| 15.3 | Compatibility matrix | Publish the harness × version table with honest labels (first-class / lower-layer / documented / not-yet), generated from the M14 runs | doc | no "supported" without a green pack | #189 | [CUJ-14](../../prd/04-users-and-cujs.md) | [PRD 19](../../prd/19-harness-compatibility.md) |
| 15.4 | Release notes + honest gaps | Release notes citing the field-test journal (M14) + the gap list ([PRD 03 §4](../../prd/03-landscape.md), [PRD 23 §1](../../prd/23-enterprise-adoption-and-hardening.md)) | doc | no over-claim; gap list matches the roadmap | #190 | [CUJ-14](../../prd/04-users-and-cujs.md) | [PRD 09](../../prd/09-roadmap.md) |
| 15.5 | **Sign + SBOM + tag + publish** | SBOM (CycloneDX), Sigstore/SLSA signed artifacts, OpenSSF Scorecard recorded; tag **`v0.1.0`**; PyPI publish | release | tag only after M14 green + audit green; artifacts verified | #191 | — | [E15](../../prd/05-features.md) |
| 15.6 | Security audit — risk re-grade | Re-grade the [PRD 08](../../prd/08-risks.md) risk register against the shipped build; record new risks + dismissed ones | doc | register updated with the shipped reality | #192 | — | [PRD 08](../../prd/08-risks.md) |
| 15.7 | Demo + docs finalize | The three demos wired ([`demo-scripts.md`](../../guides/demo-scripts.md)); README/docs reflect the built core (no "coming soon") | docs | demos ran green on the release commit | #193 | — | [PRD 00](../../prd/00-press-release.md) |
| 15.T | Tests | Release tooling + claimed-lint + audit-gate tests | tests | coverage ≥95% | #194 | — | — |
| 15.C | Coverage gate | ≥95% on release tooling | coverage report | ≥95% | #195 | — | — |
| 15.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #196 | — | — |
| 15.CR | Code review | Findings resolved | review log | no open findings | #197 | — | — |
| 15.D | Docs | Release notes, compatibility matrix, claims-lint doc, [PRD 12](../../prd/12-traceability.md) closed rows | docs | docs updated + linked | #198 | — | — |
| 15.CI | Commit & push | Feature branch (merge-ready) | git | pushed | — | — | — |
| 15.W | Update WBS | Final checkpoint in the index Progress; tag recorded | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Plan first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] **Security audit green: `trufflehog` finds 0 secrets in the tree, and a full git-history scan finds no token leak** (a finding blocks the tag)
- [ ] Claims lint green; compatibility matrix honest; release notes carry the gap list
- [ ] SBOM + signed artifacts + Scorecard recorded; **`v0.1.0` tagged** after M14 green

**Planned (opens at `15.D0`).** Release: [`docs/release/v0.1.0/`](../../release/v0.1.0/) · Audit:
[`docs/release/v0.1.0/SECURITY_AUDIT.md`](../../release/v0.1.0/) · Gate: [PRD 09 §3](../../prd/09-roadmap.md).

---

Part 8 green ⇒ **agentkeys v0.1.0 ships** — the never-in-context lifecycle, the stdio flagship, scan/migrate,
revoke ≤1s, and a green security audit. **Nothing follows M15.**
