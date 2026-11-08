# agentkeys PRD

The product requirements for **agentkeys** — the never-in-context credential broker for agents:
agents hold only *references*, real secrets stay in OS keychain / credential-file / secret-manager
backends, short-lived audience-bound tool-scoped session-bound tokens are injected **at egress**, and
one command kills all agent access in **≤1s**. Part of the
[agentic-suite](https://github.com/agentic-suite).

> **Status: draft — v0.1.0 set (plan of record).** Code has not started. This set is the design of
> record the design docs, WBS, tests, and field test are built from. Requirements are sourced from the
> ecosystem research PRD and expanded here into a product-level set with acceptance criteria; the source
> is retained verbatim as [Appendix A](appendix-a-consolidated-prd.md) with a line-by-line trace. The
> ecosystem coverage map named two *unowned* rows that this tool exists to close — **#7 credential
> revocation** (weak everywhere) and **#8 stdio MCP credential handling** (**nobody**) — plus the
> cross-harness developer-native UX that none of the enterprise brokers ship.

## Documents

| # | Document | Scope |
|---|---|---|
| 00 | [Press release / FAQ](00-press-release.md) | The one-page story and the honest FAQ (incl. "why not 1Password/Aembit") |
| 01 | [Why](01-why.md) | Problem, four credential failure modes, evidence, why now, what success looks like |
| 02 | [Architecture](02-architecture.md) | Components, credential lifecycle, trust boundaries, three egress-injection points, stdio boundary, failure semantics, deployment shapes |
| 03 | [Landscape](03-landscape.md) | What OSS, commercial, and platform-native tools already solve (Aembit, Entra, 1Password, Doppler, Infisical, Vault, agentgateway, SPIFFE/WIMSE), the whitespace, honest v0.1.0 gaps |
| 04 | [Users, stories & CUJs](04-users-and-cujs.md) | 7 personas, 28 user stories, 14 critical journeys with unhappy paths |
| 05 | [Features](05-features.md) | R1–R19 product + E1–E15 engineering requirements (with acceptance criteria) + the F1–F23 catalog |
| 06 | [Security baseline](06-security-baseline.md) | Invariants, STRIDE threat model, own threat model ("we are a target"), the stdio boundary, privacy, non-claims |
| 07 | [Success metrics](07-success-metrics.md) | Headline + spine + gate-trust + product-health metrics, anti-metrics, measurement infra |
| 08 | [Risks](08-risks.md) | Risk register with mitigations and tripwires; dismissed risks |
| 09 | [Roadmap](09-roadmap.md) | v0.1.0 → v0.1.x → v0.2.0 → v0.3.0 sequencing, exit gates, anti-scope rule |
| 10 | [Feature parity](10-feature-parity.md) | Gap-closure matrix vs Aembit/Entra/1Password/Doppler/Infisical/Vault/gateways/OSS/platform-native |
| 11 | [Decisions](11-decisions.md) | 17 frozen design decisions + 15 deferred decisions with defaults |
| 12 | [Traceability](12-traceability.md) | Requirement → story → CUJ → scenario → test; coverage-gap honesty |
| 13 | [NFRs](13-non-functional-requirements.md) | Performance, durability, portability, security, observability, usability, maintainability, privacy |
| 14 | [Non-goals](14-non-goals.md) | Hard boundaries (security properties), phase boundaries, disambiguations |
| 15 | [Data model](15-data-model.md) | Entities, `akref/1.0` + `issuance/1.0` contracts, the agentwatch event set, SQLite schema, hash chain, integrity, config |
| 16 | [Adapters & integration](16-adapters-and-integration.md) | The five adapter surfaces: per-harness recipes (Claude Code, Cursor, Codex, Gemini, Copilot), generic stdio/HTTP/exchange recipes, backend adapters, the embedder surface, ecosystem seams, adapter governance |
| 17 | [Scenarios](17-scenarios.md) | The field-test scenario catalog (SC-01…SC-53) incl. attack packs, migration/posture pack, canary pack, and the kill-time benchmark protocol |
| 18 | [Issuance integrity](18-issuance-integrity.md) | The identity chain (subject/actor/session/reference/execution credential), the issuance request pipeline, replay & spoofing defenses, step-up provenance, revoke-vs-in-flight semantics, multi-agent rules (D-17) |
| 19 | [Harness compatibility](19-harness-compatibility.md) | REQUIRED: the below-the-harness model, Tier 1/2/3 matrices, honest labels, verification |
| 20 | [Standards & claims](20-standards-and-claims.md) | RFC 8693/8707/9700/9728/9068/9449, MCP authorization + the ext-auth contribution plan, SPIFFE/WIMSE/AIMS, EU AI Act Art. 14 + NIST 800-207 deep mappings, framework mappings, claim labels + claims vocabulary, non-claims |
| 21 | [Evidence & method](21-evidence-register-and-method.md) | Evidence register, context-dump study protocol, kill-time protocol, reproducibility kit, non-evidence honesty |
| 22 | [Operations & governance](22-operations-and-governance.md) | Deployment modes, config-as-code, upgrade/backup/restore with ledger continuity, health, the 8 incident runbooks, the revoke-drill program, retention/export, governance |
| 23 | [Enterprise adoption & hardening](23-enterprise-adoption-and-hardening.md) | The honest starting point, the Stage 0–4 adoption ladder, the buyer packet, topologies, hardening principles |
| A | [Appendix A — consolidated source PRD](appendix-a-consolidated-prd.md) | The vault's PRD 04 verbatim, every line traced into the numbered set; both open questions closed (D-17) |

## Reading order

- **You want the pitch:** [00](00-press-release.md) → [01](01-why.md).
- **You want the killer demo:** [quickstart](../tutorials/quickstart.md) → [17](17-scenarios.md) §15.
- **You want to build it:** [02](02-architecture.md) → [05](05-features.md) → [15](15-data-model.md) (then [04](04-users-and-cujs.md) for the journeys).
- **You want the vision beyond v0.1.0:** [05 §D](05-features.md) (forward slate) → [09](09-roadmap.md).
- **You're a security reviewer:** [06](06-security-baseline.md) → [18](18-issuance-integrity.md) → [20](20-standards-and-claims.md) → [21](21-evidence-register-and-method.md).
- **You're a standards/compliance reviewer:** [20](20-standards-and-claims.md) → [06](06-security-baseline.md) → [12](12-traceability.md).
- **You're an enterprise buyer:** [23](23-enterprise-adoption-and-hardening.md) → [03](03-landscape.md) → [10](10-feature-parity.md) → [14](14-non-goals.md) (what we refuse to pretend).
- **You're an integrator:** [16](16-adapters-and-integration.md) → [19](19-harness-compatibility.md) → [15](15-data-model.md) → [05 §B](05-features.md) (the contracts).
- **You operate it:** [22](22-operations-and-governance.md) → [09](09-roadmap.md) → [12](12-traceability.md) → [17](17-scenarios.md).
- **You want to check us against our source:** [Appendix A](appendix-a-consolidated-prd.md) (verbatim + trace).

## Conventions

- **BLUF** — Bottom Line Up Front in every major document.
- **Honesty** — misses and limitations are documented, not hidden; "not yet" is a first-class answer.
- **Never-in-context** — no doc, example, fixture, or screenshot in this repo contains a real
  credential; only references (`env:` / `file:` / backend handle) and clearly-fake test values.
- **Versioned evidence** — every claim is labeled: *documented* (in this PRD) · *conformance* (passes a
  spec suite) · *field-tested* (from a hand-maintained field-test report) · *verified* (third-party
  reproduced). Product claims use the [claims vocabulary](20-standards-and-claims.md) exactly.
