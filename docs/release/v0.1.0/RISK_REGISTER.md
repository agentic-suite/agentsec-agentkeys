# Risk register — v0.1.0 re-grade (`15.6`)

**Addendum to [PRD 08](../../prd/08-risks.md), not a rewrite.** PRD 08 stays the plan of record; this document
records what the **shipped build and the field test** actually showed for each risk, plus the risks the sweep
surfaced and the ones we now dismiss outright.

**How to read a row:** *Observed* is the state after M14 + M15 — **reduced** (a control now demonstrably works),
**unchanged** (the mitigation shipped; the residual is what PRD 08 described), **increased** (the sweep found it
sharper than assumed), **closed** (no longer applies), **accepted** (we live with it, with a tripwire).

| # | Risk | Observed | What the build / field test showed |
|---|---|---|---|
| **R-1** | Broker compromise — we are a target | reduced | Self-attack packs run in CI and passed: spoofed reference, tampered config, rewritten ledger, widened scope, "disable the broker" (FT-AP-TAMPER, FT-AP-WIDEN, FT-LA-TAMPER). Secrets never persisted: context dump found 0 usable, evidence scan found 0 secrets with the seeded leak caught. Residual is unchanged: an attacker with the broker's own runtime wins — documented, not hidden. |
| **R-2** | stdio co-located-runtime hard case | unchanged | FT-ST-NOSECRET passes (a stock stdio child authenticates with no secret in config/env/transcript) and FT-DK-BOUNDARY passes in containers. The co-located same-runtime case is still **not protectable**; the report and PRD 06 §4 say so. The mitigation is the process boundary, and it is now tested rather than asserted. |
| **R-3** | Backend outage denies the agent | reduced | The fail-closed matrix is 6/6 (FT-FC-ABSENT/CONFIG/STORE/SINK/CRASH/LOCKED): outage denies **new** issuance and never degrades to a static secret. `doctor` explains the effective backend. The denial is now a measured behaviour, not a claim. |
| **R-4** | MCP spec step-change breaks the stdio pattern | unchanged | The injection layer stayed transport-agnostic (env / header / RFC 8693). No spec change occurred during the sweep, so the risk is neither reduced nor increased — the tripwire (a draft MCP revision changing stdio credential guidance) remains the trigger. |
| **R-5** | Enterprise incumbents are "good enough" | unchanged | Not testable on one box. What changed: the honest gap list now names SSO/SCIM, multi-tenant, fleet and cloud backends as *not yet*, so an evaluator is not surprised later. |
| **R-6** | A platform absorbs the idea | unchanged | No tripwire fired during the sweep. The moat argument (below the harness, off the network path, stdio included) is unchanged; the published benchmark is the reusable evidence. |
| **R-7** | Adoption friction — developers keep pasting keys | reduced | `scan` → `migrate` passes end-to-end on the seeded fixture with 100% recall and 0 printed values (FT-MP-SCANMIGRATE), and the fresh-venv install → first brokered call path completes in 2.7s. The remaining gap is a naive-human fresh-machine median — a WARN, not a pass. |
| **R-8** | Standards / skill drift | unchanged | Conformance rows are green (FT-CONF-STANDARDS/BACKENDS) with DPoP explicitly **not supported**. Drift is a future event; the tripwire stays. |
| **R-9** | Supply-chain compromise | reduced | Runtime dependency set is empty and asserted against `pyproject.toml` (FT-SC-INREPO); the SBOM is generated; `security.txt` and the CI gates are checked. Signing/attestation is **not done**: this is an **unsigned release by decision**, so the "signed release" part of the mitigation is unevidenced — no signature claim is made anywhere, and verifying is checksum + SBOM + a re-run of the audit. |
| **R-10** | Over-claiming destroys trust | reduced | This is now mechanically enforced: 18 claims, 0 over-claims, 0 verified, WARN evidence capped at *documented*, banned superlatives scanned in public docs ([CLAIMS_LINT.md](CLAIMS_LINT.md)). The risk is not zero — a claim made outside the repo (a blog post, a talk) is outside the lint. |
| **R-11** | Store/ledger corruption blocks issuance — or silently diverges | reduced | `verify-log` recomputes the chain and reports tamper; FT-LA-TAMPER and FT-OPS-* (backup/restore/drill/migrate) pass; the single-writer lock is enforced in containers (FT-DK-SINGLEWRITER). |
| **R-12** | Single-maintainer / bus factor | increased | The sweep made this sharper, not better: the release depends on one person's credentials for signing and publishing, and the field-test WARNs (live harness runs) need a human who is logged in. Recorded as a real risk with a concrete mitigation path below. |

## New risks surfaced by the field test

| # | Risk | Why it is new | Mitigation now in place |
|---|---|---|---|
| **N-1** | **Harness trust** — the evidence is only as good as the tooling that produced it | The sweep found 12 defects; **all 12 were in the harness or the environment, none in the product**. Before that, "the runner said pass" was the only check. | The verifier re-derives every assertion from committed results; leak scan, traceability and a report guard ship with the harness; the harness self-test runs on temp copies only. |
| **N-2** | **Allowlist rot** — a narrow secret allowlist can silently widen | The audit needed a by-value gitleaks allowlist for synthetic fixtures; a future edit could turn it into a path or shape wildcard and blind the scanner. | The allowlist is by exact value only, and a test fails on any wildcard or shape pattern. A new planted value fails the audit until a human adds it deliberately. |
| **N-3** | **Scanner silence** (a scanner that never fires) — a scanner that finds nothing looks identical to a scanner that is broken | trufflehog did **not** fire on the first control shape (an AWS key ID); a naive audit would have reported "clean". | The control is dual-scanner (DSN for trufflehog, high-entropy assignment for gitleaks) and a half-awake control denies the audit. |
| **N-4** | **Single-maintainer concentration in the release path**, and **stale public docs** — README can claim "not yet" for shipped features, or "coming soon" for what never shipped | The README still described M14 as future work at the time of this re-grade. A stale doc is a false claim by omission. | `15.7` reconciles README/docs with the built CLI; the claims lint scans public prose; the docs-link test runs in CI. |

## Dismissed risks (and the reason)

| Risk | Why dismissed |
|---|---|
| **"Users will run an unsupported harness and blame us."** | The compatibility matrix makes every row's label explicit — first-class / lower-layer / documented / not yet — and no row claims *supported* without a green pack. A missing row is now **visible**, which is the whole point. |
| **"A leaked token in an old commit blocks the release forever."** | Dismissed as a *remediation* risk, not a *detection* risk: detection is automated (tree + full history), and the policy is rotate + fix forward, never a history rewrite. A real finding still blocks the tag until it is rotated. |
| **"The benchmark will be gamed by a slow machine."** | Dismissed because the claim is explicitly field-tested on one disclosed machine class, and a slower number is a valid published result unless it exceeds the ≤1s budget on p95 *and* max. |

## Tripwires to watch (next release)

- A real credential found in history → rotate, fix forward, re-run the audit; **never** rewrite history.
- A scanner update that stops firing on the control → the audit denies until the control is fixed (by design).
- Any public claim that cannot resolve to a case id → the claims lint fails.
- A harness whose live leg gets unblocked → its row moves from *documented* to *first-class* **only** with a
  green pack.
