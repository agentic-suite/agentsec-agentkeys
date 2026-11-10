# Release plan — v0.1.0 (M15 · `15.D0`)

**BLUF:** v0.1.0 ships only if **three hard gates are green on the release commit**: the **secret-leakage
audit** (tree + full git history), the **claims lint** (no claim wears a label above its evidence), and the
**M14 field test** (71 PASS · 0 FAIL · 3 WARN). Everything else in this milestone — the compatibility matrix,
the release notes, the SBOM, the risk re-grade, the demos — is produced **from committed evidence**, never
from optimism. The tag is the last step, not the first.

- **WBS:** [`wbs-v0.1.0-part8-fieldtest-release.md`](../../wbs/v0.1.0/wbs-v0.1.0-part8-fieldtest-release.md) — M15
- **Owning requirements:** [E15](../../prd/05-features.md), [PRD 06 §5](../../prd/06-security-baseline.md),
  [PRD 09 §3](../../prd/09-roadmap.md), [PRD 19](../../prd/19-harness-compatibility.md),
  [PRD 20 §6–§7](../../prd/20-standards-and-claims.md), [PRD 23 §1](../../prd/23-enterprise-adoption-and-hardening.md)
- **CUJ:** [CUJ-14](../../prd/04-users-and-cujs.md) (enterprise honesty)
- **Inputs:** `field-test/v0.1.0/results/` (74 committed verdicts), `bench/`,
  [`docs/field-test/v0.1.0/FIELD_TEST_REPORT.md`](../../field-test/v0.1.0/FIELD_TEST_REPORT.md) (hand-maintained)

---

## 1. Gate checklist (execution order)

| # | Item | Issue | Gate this produces | Blocking? |
|---|---|---|---|---|
| 15.D0 | Plan (this file) | #186 | the release contract | — |
| 15.1 | Security audit — secret leakage | #187 | `trufflehog` tree + history = 0 verified; planted-fake control fires | **yes — blocks the tag** |
| 15.2 | Claims lint | #188 | zero over-claims vs [PRD 20 §6/§6a](../../prd/20-standards-and-claims.md) | **yes** |
| 15.3 | Compatibility matrix | #189 | no "supported" row without a green pack | **yes** |
| 15.4 | Release notes + honest gaps | #190 | notes cite the field journal; gaps named | **yes** |
| 15.5 | SBOM + signed artifacts + tag + PyPI | #191 | tag only after the above are green | **yes — irreversible** |
| 15.6 | Risk re-grade | #192 | PRD 08 register matches shipped reality | yes |
| 15.7 | Demo + docs finalize | #193 | demos green on the release commit; no "coming soon" | yes |
| 15.T | Tests | #194 | release tooling + lint + audit-gate tests, coverage ≥95% | milestone gate |
| 15.C | Coverage | #195 | ≥95% on release tooling | milestone gate |
| 15.L | Lint & type | #196 | `ruff` zero · `mypy --strict` clean | milestone gate |
| 15.CR | Code review | #197 | no open findings | milestone gate |
| 15.D | Docs | #198 | release docs + PRD 12 rows closed | milestone gate |

Gate items (`.T`/`.C`/`.L`/`.CR`/`.D`) run **once at the end of the milestone**, never per ticket.

---

## 2. Security audit scope (`15.1`)

**Question the audit answers:** *is there a live credential anywhere a stranger can read it — in the working
tree, in any commit, on any branch?* One finding in history blocks the tag.

### 2.1 Scope

| Surface | Tool | Pass condition |
|---|---|---|
| Working tree (tracked + untracked, excluding `.git`) | `trufflehog filesystem` | 0 verified secrets |
| **Full git history, all branches, all refs** | `trufflehog git --branch` (no `--since-commit`) | 0 verified secrets |
| Second scanner, independent ruleset | `gitleaks detect --log-opts=--all` | 0 findings |
| Store, exports, fixtures, committed field results | entropy + pattern scan (existing `scan_results.py` patterns) | 0 hidden/usable secrets |
| `security.txt` + repo hygiene | `agentkeys.supplychain.run_supply_checks` | all checks green |

### 2.2 The control (a scanner that never fires is not a gate)

The audit ships with a **planted-fake control**: a temporary file carrying a known-fake credential shape is
written to a temp directory, the scanner must flag it, and the temp file is removed. If the control does not
fire, the audit is a **FAIL** — a silent scanner cannot certify anything. The control runs on a temp copy only;
the audit never writes to the real tree, the results tree, or the report.

### 2.3 Remediation policy

- A live credential **anywhere** (tree or history) → **rotate the credential first**, then fix forward in a new
  commit. **Never** rewrite pushed/shared history to scrub a secret (the scrub buys nothing; the token is
  already compromised) — codified in [`AGENTS.md`](../../../AGENTS.md) after a prior incident.
- A **fake** credential in a fixture is not a finding, but it must be recognisable as fake (`_PLANTED_VALUE`
  style) and must not be echoed into committed evidence (M14 leak gate already enforces this on results).

### 2.4 Deliverables

- `src/agentkeys/release/audit.py` — runs the scanners, normalises results, enforces the control, returns a
  structured report (never a bare exit code — see [PRD 21](../../prd/21-evidence-register-and-method.md)).
- `docs/release/v0.1.0/SECURITY_AUDIT.md` — the report: commands, versions, commit SHA, result per surface,
  control result, and the honest limits of what the scanners do not see.
- `.github/workflows/release-audit.yml` — the CI gate (runs on `push` to release branches and `workflow_dispatch`).
- Tests: control fires, control failure is a FAIL, a planted tree secret is caught, clean tree passes,
  history mode is requested (not `--since-commit`), report shape is stable.

**Honest limit:** these scanners find credential *shapes*. A live credential with no recognisable shape is not
caught by entropy or rules; the ledger/redaction invariants (R6, PRD 06 §5) are what keep secrets out of stored
artefacts in the first place.

---

## 3. Claims lint scope (`15.2`)

**Question the lint answers:** *does any public sentence use a stronger word than its evidence supports?*

### 3.1 The vocabulary being enforced

From [PRD 20 §6](../../prd/20-standards-and-claims.md): **documented → conformance → field-tested → verified**.
From [PRD 20 §6a](../../prd/20-standards-and-claims.md): the product terms **brokered**, **reference-only**,
**audience-bound**, **tool-scoped**, **session-bound**, **revocable ≤1s**, **first-class recipe**,
**lower-layer coverage**, **field-tested**, **verified**.

### 3.2 Files in scope (public claims)

- `README.md`, `CHANGELOG.md`, `SECURITY.md`
- `docs/release/v0.1.0/*.md` (notes, compatibility matrix, audit)
- `docs/reference/*.md`, `docs/guides/**/*.md`, `docs/explanation/*.md`
- `docs/prd/*` is **exempt** (it is the specification of intent, not a claim about the build)

### 3.3 Rules

1. **`verified`** may appear only where an independent third party re-ran the published artefact. At v0.1.0
   nothing is `verified`; the word is a **finding** outside a quoted non-claim.
2. **`field-tested`** requires a row in the hand-maintained report. The lint resolves the claim to a case id.
3. **`conformance`** requires a green conformance case id (e.g. `FT-CONF-STANDARDS`, the RFC suites).
4. **`first-class recipe`** requires *both* a shipped recipe *and* its pack green. Otherwise the honest label is
   **lower-layer coverage** or **documented**.
5. **`supported`** on a platform/harness row requires a green pack for that harness + version; otherwise the row
   says *documented*, *lower-layer*, or *not yet*.
6. **Non-claims** ([PRD 20 §7](../../prd/20-standards-and-claims.md)) must stay present: not a compliance
   certification, not an injection detector, not proof-of-possession, not protection from a co-located runtime,
   not an identity provider, not a vault.

### 3.4 Deliverables

- `src/agentkeys/release/claims.py` — the linter (rule → file:line → offending term → suggested honest label).
- `docs/release/v0.1.0/CLAIMS_LINT.md` — the result table: claim → label → evidence row → verdict, plus the
  named gaps (nothing smoothed).
- Tests: each rule has a positive case (a real violation is caught) and a negative case (honest usage passes);
  a `verified` claim fails; a `field-tested` claim with no evidence row fails; the non-claims block is required.

**Design decision:** the lint is **targeted and evidence-linked**, not a general prose linter. It fails on
*known strong terms in public files*, and it checks claims against the committed field results rather than
against a hand-written allowlist — otherwise it would be a spell-checker with a security theatre badge.

---

## 4. Compatibility matrix scope (`15.3`)

**Rule:** no row says "supported" without a **green pack** for that harness + tested version
([PRD 19 §6](../../prd/19-harness-compatibility.md)).

Labels allowed per row: **first-class recipe** · **lower-layer coverage** · **documented** · **not yet**.

Source of truth = the M14 results, not intent:

| Harness | v0.1.0 label | Evidence |
|---|---|---|
| Claude Code | **documented** (recipe + wiring green; live call blocked) | `FT-HC-CLAUDE` — **WARN**: `claude` 2.1.187 installed, wiring + smoke green, headless run returns `Not logged in · Please run /login` |
| Cursor | **documented** (recipe shipped; no headless surface on the test box) | `FT-HC-CURSOR` — **WARN**: GUI IDE, no headless CLI |
| GitHub Copilot | **lower-layer coverage** (documented) | [PRD 19 §3](../../prd/19-harness-compatibility.md); no pack |
| Codex CLI · Gemini CLI | **not yet** | [PRD 19 §3](../../prd/19-harness-compatibility.md) |
| Tier 2 frameworks | **documented** (not pack-gated) | [PRD 19 §4](../../prd/19-harness-compatibility.md) |
| Tier 3 / enterprise | **documented** (standards-based, not individually verified) | [PRD 19 §5](../../prd/19-harness-compatibility.md) |
| Platforms: macOS / Linux · Windows | **supported (field-tested)** · **not supported** | `FT-CONF-*`, `FT-NFR-PORT`; README states Windows unsupported |

Deliverable: `docs/release/v0.1.0/COMPATIBILITY.md`, generated from the committed results by a small
generator (`agentkeys.release.compat`) so a missing pack makes a missing row **visible**, plus a test asserting
no row is labelled "supported"/"first-class" when its case is not PASS.

---

## 5. Release notes + honest gaps (`15.4`)

- Release notes cite the **hand-maintained** field journal (M14) — counts, the blocking five, the three named
  WARNs, and the fail→fix→green arc. No number that is not in the committed results.
- Gap list from [PRD 23 §1](../../prd/23-enterprise-adoption-and-hardening.md) and
  [PRD 03 §4](../../prd/03-landscape.md): SSO/SCIM, multi-tenant/RBAC/WORM, certification, fleet control,
  cloud backends, Windows, DPoP, co-located runtime — each labelled *not yet* / *mapped only* / *documented*.
- Entered into `CHANGELOG.md` as `[0.1.0]` **only after** the gates are green (the file already commits to this).

---

## 6. SBOM, signing, tag, publish (`15.5`) — the irreversible steps

Ordered, each step gated on the previous:

1. **SBOM** — `agentkeys.supplychain.build_sbom` → CycloneDX JSON committed to `docs/release/v0.1.0/`.
2. **Build artifacts** — `python -m build` (sdist + wheel) into `dist/`.
3. **Signing / attestation** — Sigstore (`sigstore` / `cosign`) over the artifacts, plus SLSA provenance.
   **Requires release credentials**; if they are unavailable the step is recorded as **BLOCKED**, not skipped
   silently, and the tag carries that stated limitation.
4. **OpenSSF Scorecard** — the existing `.github/workflows/scorecard.yml` result recorded in the release doc.
5. **Tag `v0.1.0`** — only after 15.1–15.4 are green **and** M14 is green.
6. **PyPI publish** — only after the artifacts verify.

**Stop rule:** steps 3, 5 and 6 are irreversible and/or require the maintainer's credentials. This plan
prepares every artefact and then **halts for explicit go-ahead** before tagging or publishing.

---

## 7. Risk re-grade (`15.6`)

Re-read [PRD 08](../../prd/08-risks.md) against the shipped build: for each `R-n`, record the **observed** state
(mitigation actually shipped? tripwire fired during M14?), any **new** risk surfaced by the field test, and each
**dismissed** risk with the reason. Output: `docs/release/v0.1.0/RISK_REGISTER.md` (an addendum to PRD 08, not a
rewrite of it — PRDs are not renumbered or rewritten).

---

## 8. Demos + docs finalize (`15.7`)

- The three demos in [`docs/guides/demo-scripts.md`](../../guides/demo-scripts.md) run green on the release commit.
- README/docs reflect the **built** core: remove or fix any "not yet" that has since shipped, and remove any
  "coming soon" that the release does not deliver. Cross-check `docs/reference/cli.md` against the real CLI.

---

## 9. Milestone gates

| Gate | Command | Pass |
|---|---|---|
| 15.T | full suite | green, no skips masking failure |
| 15.C | `pytest --cov=agentkeys --cov-fail-under=95` | ≥95% |
| 15.L | `ruff check` + `ruff format --check` + `mypy` | zero / clean |
| 15.CR | review log | no open findings |
| 15.D | docs + PRD 12 rows | updated + linked |

Recorded once, in the WBS index Progress, with the exact command, result and commit.

---

## 10. Non-goals for this milestone

- No history rewrite, ever.
- No new product features — M15 produces evidence and releases, it does not add capability.
- No claim promoted beyond its evidence because it is release day. A claim that cannot earn its label is
  **downgraded in the text**, not upgraded in the label.
