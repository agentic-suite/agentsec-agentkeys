# PRD 23 — Enterprise Adoption & Hardening

**BLUF:** agentkeys v0.1.0 is honest about what it is: a **local-first, single-user broker with no SSO, no
multi-tenant mode, and no compliance letters** — and that is the correct starting point, not an apology.
Enterprises do not adopt tools like this by flipping a procurement switch; they adopt them by **staging**:
a developer proves it locally → a team standardizes on it → the fleet gets a server → the fleet gets real
identity → the org gets certifications. This document is that ladder, honestly: **Stage 0–4** with the
exit criteria for each, the **buyer packet** (what an enterprise reviewer receives today, with the gap
matrix front and center), the **topologies** it eventually serves (laptop fleet, CI runners, server-side
agents), and the **hardening principles** that hold at every stage. What we refuse to do is *pretend* to
be at Stage 4 — the fastest way to lose a security buyer is to be caught over-claiming.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. The honest starting point (what an enterprise gets on day one)

| They ask | The honest v0.1.0 answer |
|---|---|
| SSO / SCIM / directory sync | **Not yet** — local OS principal; identity is consumed at R12 |
| Multi-tenant / RBAC / WORM | **Not yet** — single-user store; retention is explicit and local ([PRD 22 §8](22-operations-and-governance.md)) |
| SOC 2 / ISO 27001 / ISO 42001 | **Mappings only** — the controls map ([PRD 20 §4](20-standards-and-claims.md)); certification is roadmap (v1.x) |
| Central fleet control | **Not yet** — R11; today every machine runs the same local semantics |
| Cloud backends | **Not yet** — keychain + file at v0.1.0; 1Password/Vault/K8s/cloud SM at R10 |
| Supply chain assurance | **Yes, now** — signed releases, SLSA provenance, SBOM, OpenSSF Scorecard, `security.txt` (E15) |
| Auditable evidence | **Yes, now** — hash-chained ledger, secret-free export, `verify-log`, per-session reconstruction (R6, E12) |
| Standards alignment | **Yes, now** — RFC 8693/8707/9700/9728/9068 conformance-gated; WIMSE/AIMS-aligned (E13, [PRD 20](20-standards-and-claims.md)) |

The two "yes, now" rows are why an enterprise evaluator keeps reading: the evidence pipeline starts on day
one, not at Stage 4.

## 2. The adoption ladder (Stage 0 → 4)

| Stage | Who | What they run | Exit criteria (to the next stage) |
|---|---|---|---|
| **0 — Prove locally** | One engineer (Maya) | Local broker; `scan`/`migrate` one credential; one harness recipe | A real authenticated tool call with zero secrets in context; a revoke drill < 1s on their own machine |
| **1 — Standardize the team** | The team | Config-as-code in the repo; step-up policy in agentpolicy (prod class); posture review in CI | Every team credential brokered or on the posture report's exception list; no literal secret merged in a quarter |
| **2 — Fleet broker** | The platform team | R11: central broker, cluster-safe store, parent→child delegation, per-team policy namespaces | Delegation proven monotonically narrowing; fleet revoke drill; CIS-benchmarked manifests |
| **3 — Real identity** | Security org | R12: SPIFFE/WIMSE SVIDs as actor tokens; R14: DPoP where targets support it | Actor identity conformance green; stolen-token-string fixtures fail for the same audience |
| **4 — Certifications** | GRC (Dana) | SOC 2 Type I → II, ISO 27001; FIPS-mode operation | Audit letters in hand; the evidence pipeline already produced the artifacts (started at Stage 0) |

**Why this order:** every stage's exit criteria are produced by tooling from the *previous* stage — the
evidence doesn't start when the certifier arrives; it starts at Stage 0. That is the whole trick: the
ledger, the export, and the drills are the audit, six months early.

## 3. The buyer packet (what a reviewer receives today)

1. **The gap matrix** — [PRD 03 §4](03-landscape.md) and §1 above: what we do not have, stated before what
   we do. No over-claim anywhere in the docs ([PRD 20 §7](20-standards-and-claims.md)).
2. **The standards map** — implemented (conformance-gated) vs aligned vs scheduled
   ([PRD 20 §1–§2](20-standards-and-claims.md)).
3. **The compliance mappings** — OWASP LLM/Agentic, NIST AI RMF + 800-207, ISO 42001, EU AI Act Art. 14,
   MITRE ATLAS, CSA NHI ([PRD 20 §4](20-standards-and-claims.md)).
4. **The evidence plan** — kill-time and zero-secret protocols, reproducible benchmark, labels
   ([PRD 21](21-evidence-register-and-method.md)) — with today's honest state: *documented*, moving to
   *conformance* at first release.
5. **The threat model** — our own, in the open, including "we are a target"
   ([PRD 06 §3](06-security-baseline.md)).
6. **The roadmap with gates** — what lands when, and what each release proves
   ([PRD 09](09-roadmap.md)).

## 4. Topologies (what enterprises actually deploy)

| Topology | Agents | Broker shape | Notes |
|---|---|---|---|
| **Laptop fleet** | Claude Code / Cursor / Codex / Gemini CLI per developer | Local broker per machine today; R11 fleet mode later | The Stage 0–2 path; posture reports roll up via config repo review |
| **CI runners** | Headless coding agents in GitHub Actions/GitLab | Broker on the runner; credentials from the runner's backends (R10: cloud SM) | Exit codes and the ledger give the pipeline a real gate; revocation answers "kill the runaway CI agent" |
| **Server-side agents** | Long-running service agents | R11 server broker + R12 workload identity (SVIDs) | Aembit's shape, OSS-ified; the local guarantees hold as the floor |
| **Air-gapped** | Any of the above, no egress | Local backends only | A first-class mode, not an afterthought (CUJ-11, SC-39) |

## 5. Hardening principles (hold at every stage)

1. **The invariants are the floor, everywhere** — never-in-context, fail-closed, ≤1s revoke, no
   passthrough. Fleet mode does not relax a local guarantee ([PRD 09 §9](09-roadmap.md)).
2. **Separation of duties scales** — the broker holds, agentpolicy decides, the enforcer blocks, agentwatch
   observes. No stage merges two of those ([PRD 06 §3](06-security-baseline.md)).
3. **Enterprise features add identity, never ambient trust** — SSO changes *who is asserted*; it never
   introduces a standing credential or a passthrough.
4. **Every claim keeps its label** — an enterprise deck that says "field-tested" without the hand-maintained
   report is a lie; our labels travel with the claims ([PRD 20 §6](20-standards-and-claims.md)).
5. **The vendor is a target too** — supply-chain posture (E15) is part of the enterprise offer, not repo
   hygiene. Plugin4Shell was a supply-chain attack on this exact audience.

## 6. What we refuse to fake (even for a signed PO)

No SSO "coming soon" slide labeled as shipped; no SOC 2 badge before the audit letter; no "works with your
vault" before the conformance suite is green; no kill-time number from a laptop labeled as a fleet result;
no shared-session inheritance "for convenience" (D-17). A smaller true claim beats a bigger false one —
that is the whole product strategy, and it is why the gap matrix leads the buyer packet.

## 7. Related documents

- The honest v0.1.0 gaps: [PRD 03 §4](03-landscape.md), [PRD 14](14-non-goals.md).
- The roadmap each stage lands on: [PRD 09](09-roadmap.md).
- Operating it at any stage: [PRD 22](22-operations-and-governance.md).
- Parity vs the enterprise incumbents: [PRD 10](10-feature-parity.md).
