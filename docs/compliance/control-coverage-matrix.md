# Control-coverage matrix — OWASP · MITRE ATLAS · NIST

**BLUF:** The honest map from *risk* to *our control* to *our evidence* — the doc a security reviewer
audits line by line. Three rules hold throughout: (1) every mapping names the **requirement** that
implements it; (2) every claim wears its [evidence label](../prd/20-standards-and-claims.md) (§6) — today
everything is *documented*, moving to *conformance* at first release; (3) **unmapped risks stay on the
page** — a coverage matrix that hides its gaps is marketing, not mapping. The summary lives in
[PRD 20 §4](../prd/20-standards-and-claims.md); this is the full matrix.

**Status:** design of record (v0.1.0) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. OWASP Top 10 for LLM Applications (2025)

| # | Risk | agentkeys control | Requirement | Evidence | Honest gap |
|---|---|---|---|---|---|
| **LLM01** | Prompt injection | **Architectural mitigation, not detection**: nothing usable in context to exfiltrate; egress tokens bound, short-lived, single-use | R1, R3 | Context-dump pack (SC-40) | Injection itself remains unsolved industry-wide — we remove the **payoff**, not the vector |
| **LLM02** | Sensitive information disclosure | Reference-only context; redaction-before-persistence with receipts; secret-free export | R1, E5 | Evidence scanner (SC-43) | Agent-authored content outside our egress paths is not DLP'd until R16 |
| **LLM03** | Supply chain | Our own: Sigstore/SLSA/SBOM/pinned deps/Scorecard; OSS-Fuzz for parsers | E15 | Release attestations | Third-party MCP servers themselves remain un-vetted until R15 (attestation feed) |
| **LLM04** | Data & model poisoning | Out of our lane — posture/evidence only | — | — | **Unmapped by design** ([PRD 14](../prd/14-non-goals.md)) — we do not pretend |
| **LLM05** | Improper output handling | Tool/agent text is data, never a credential path; evasion detection on raw-credential reads | R7, E5 | Evasion pack (SC-14…17) | Downstream apps mishandling *their own* outputs are out of scope |
| **LLM06** | Excessive agency | Per-tool scope; step-up for prod class; (R13) blast-radius budgets | R3, R9, R13 | Step-up scenarios (SC-33/34) | Budgets are P2 — today's ceiling is the binding, not a quota |
| **LLM07** | System prompt leakage | Reference model makes prompts credential-free by construction | R1 | Context-dump pack | Secrets never in prompts is ours; proprietary-prompt leakage is a harness concern |
| **LLM08** | Vector & embedding weaknesses | Out of our lane | — | — | **Unmapped by design** |
| **LLM09** | Misinformation | Out of our lane | — | — | **Unmapped by design** |
| **LLM10** | Unbounded consumption | Spend/rate limits are LiteLLM/gateway territory; (R13) budgets compose via agenthalt | R13 | — (P2) | Not our control until R13; we compose, not compete |

## 2. OWASP Agentic AI Top 10 (draft — tracking it per the ecosystem commitment)

The draft vocabulary (identity confusion, excessive agency, memory poisoning, …) maps onto the same
controls; the binding row is the deepest:

| Draft theme | agentkeys control | Requirement |
|---|---|---|
| **Identity confusion** (agent ≠ user ≠ tool) | The identity chain: subject / actor / session / execution credential, each asserted by exactly one party; RFC 8707 audience per token | R3, [PRD 18 §2](../prd/18-issuance-integrity.md) |
| **Excessive agency** | Tool-scoped, session-bound issuance + step-up | R3, R9 |
| **Memory poisoning / cross-session contamination** | Session binding dies with the conversation; no ambient inheritance between agents (D-17) | R3, D-17 |
| **Uncontrolled credential access** | The entire product; plus evasion detection on out-of-broker reads | R1–R7 |

*Commitment: within a week of final publication, this repo publishes the finalized mapping — being first
with an honest coverage matrix is the distribution play ([PRD 20 §4](../prd/20-standards-and-claims.md)).*

## 3. MITRE ATLAS (credential-access / exfiltration-relevant techniques)

| ATLAS-shaped technique | Our answer | Requirement |
|---|---|---|
| Steal application access tokens / session tokens | Nothing standing in context; tokens single-use, bound, minutes-scale | R3, E3 |
| Unsecured credentials: files in environment | scan/migrate removes them; evasion flags reads of the leftovers | R7, R17 |
| Abuse elevation / confused deputy | Audience binding + no passthrough (E14); monotonic delegation at R11 | R3, D-17 |
| Impair defenses (kill/disable the security tool) | Broker outside the agent's control plane; tamper = fail-closed + loud event | E10 |
| Exfiltration over a tool channel | Egress-only injection means the agent never holds the exfiltrate-able thing | R2 |

*Our incident register feeds mappings back ([PRD 01](../prd/01-why.md)); the goal is contributing
detection/event rules upstream once the event set is live.*

## 4. NIST alignment (AI RMF · 600-1 · SP 800-207 · SSDF)

| Framework | Our alignment |
|---|---|
| **AI RMF "Manage/Govern"** | The hash-chained lifecycle ledger is governance evidence: every grant attributable, reconstructable, exportable (R6) |
| **AI 600-1 (GenAI profile)** | Context-minimization and least-privilege map to the reference model and per-tool scope (R1, R3) |
| **SP 800-207 (zero trust)** | No standing credential; per-request mint; audience enforced at our egress even if the target doesn't ([PRD 20 §4a](../prd/20-standards-and-claims.md)) |
| **SSDF (SP 800-218)** | Our own SDLC: signed releases, provenance, SBOM, fuzz targets, disclosed vuln handling (E15) |

## 5. Reading the matrix honestly

- **Labels**: every row above is *documented* until its suite is green (*conformance*) or its verdict is
  hand-recorded (*field-tested*). Nothing here is certification — we map, we don't attest ([PRD 20 §7](../prd/20-standards-and-claims.md)).
- **Unmapped rows stay**: LLM04/LLM08/LLM09 are named as out-of-lane rather than stretched to fit —
  over-mapping is the same sin as over-claiming.
- **The gaps column is the point**: each row names what we do *not* cover, because a reviewer who finds
  our gap before we name it stops trusting the rest of the page.

## Related

- The one-page standards summary: [PRD 20 — Standards & claims](../prd/20-standards-and-claims.md)
- The invariants behind the controls: [PRD 06 — Security baseline](../prd/06-security-baseline.md)
- The evidence method: [PRD 21](../prd/21-evidence-register-and-method.md)
