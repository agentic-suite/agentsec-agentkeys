# PRD A — Appendix A: Consolidated Source PRD (verbatim)

**BLUF:** This is the source document the entire numbered set was built from — the ecosystem research
PRD for agentkeys, retained **verbatim** so every line of it stays auditable against the expanded set. The
numbered PRDs ([00](00-press-release.md)–[23](23-enterprise-adoption-and-hardening.md)) inherit and expand
it; nothing here is silently dropped — the trace table at the bottom maps every source line to where it
now lives. Two of its open questions are now **answered** (§7 → frozen decisions), which is what
"plan of record" means: questions get closed in writing, not forgotten.

**Status:** Source retained verbatim (2026-09-27) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

---

> **Provenance:** `research/agent-security/ecosystem/prds/213-agentkeys.md` (the vault's "PRD 04 —
> agentkeys"). Reproduced below without edits; its relative links (`../../03-product-landscape/…`,
> `../../02-threat-landscape/…`, `../00-harness-compatibility.md`) point into the **research vault** and
> are kept as-is for fidelity — a link checker will flag them by design. The local destinations for that
> content are [PRD 03](03-landscape.md), [PRD 01](01-why.md), and [PRD 19](19-harness-compatibility.md).

---

## 1. Why (problem + evidence)

1. Credential revocation is the weakest capability across the entire landscape: commercially only Aembit/Entra; in OSS only single-maintainer experiments ([coverage map](../../03-product-landscape/04-coverage-map-commercial-vs-oss.md) row #7).
2. STDIO MCP credential handling is covered by **nobody** (row #8): local servers read static secrets from env vars — no audience binding, no revocation — the vector behind multiple documented incidents.
3. The only defense class every expert/skeptic universally endorses is capability-scoped, session-bound, short-lived credentials (contrarian research, [evidence file](../../02-threat-landscape/03-incidents-and-evidence.md)).
4. "The agent leaked its key" currently costs a quarter of key rotation; it should cost one command.

## 2. What (requirements)

### P0 — Must have (v1.0)
| # | Requirement | Acceptance criterion |
|---|---|---|
| R1 | Agents hold only **references**; real secrets never rendered into agent context, arguments, or logs | Simulated full context-dump attack pack (PRD 09) finds zero usable credentials |
| R2 | Real credentials resolved at moment-of-use, injected at egress only | Agent completes a real authenticated tool call without ever seeing the secret |
| R3 | Token model: short-lived, audience-bound (one server), tool-scoped (one tool), session-bound (dies with conversation) | Each binding property demonstrated by an attempt to replay/reuse the token elsewhere — fails |
| R4 | `agentkeys revoke <agent|session|all>` kills all issued tokens and brokered access in ≤1s | Revocation replay-verified in automated test |
| R5 | Backends at launch: OS keychain; credential files on disk as fallback | Documented backend matrix; backend failure semantics defined (fail-closed) |
| R6 | Every issuance/use/upgrade/revocation as an agentwatch-schema event | Full credential-lifecycle audit for any session reconstructable |
| R7 | Secret-evasion detection: attempts to read env/file credentials outside the broker flagged as high-severity events | Evasion attack pack caught in monitor-only mode |

### P1 — Should have (v1.x)
- R8: 1Password/Vault/K8s-secret backends.
- R9: Step-up issuance: token upgrades require policy approval (human `ask` for prod-class credentials) — with PRD 02.
- R10: STDIO-server specialization: transparent credential virtualization for local MCP servers (the unowned row #8 gap — flagship use case).

### P2 — Nice to have
- R11: SPIFFE-based workload identity for server-side agents.
- R12: Credential health reports: what agents hold what classes of access, exposure-age scoring.

## Harness Compatibility — REQUIRED (agnostic or explicitly compatible)

> **Non-negotiable:** this tool must be agentic-harness-agnostic or explicitly harness-compatible. It may never be built for a single harness — it either works across harnesses by construction (protocol/kernel/OTel/identity layers) or ships named adapters with a published compatibility table. agentdrill verifies compatibility with per-harness attack packs.

**Compatibility targets — most popular agentic harnesses/ecosystems (ordered by user base; full matrix: [00-harness-compatibility.md](../00-harness-compatibility.md)):**

| Tier | Harness / Ecosystem | Requirement |
|---|---|---|
| 1 — Coding agents | **Claude Code** · **Cursor** · **GitHub Copilot** (agent mode) · **OpenAI Codex CLI** · **Gemini CLI** | ≥2 Tier-1 at v0.1.0; all 5 by v0.3.0 (or documented lower-layer coverage where closed, e.g. Copilot) |
| 2 — Agent frameworks | **LangChain/LangGraph** · **CrewAI** · **OpenAI Agents SDK** · **AutoGen/AG2** · **LlamaIndex** · **PydanticAI** · **smolagents** | ≥3 framework adapters by v0.3.0 where the tool has an SDK surface (agentwatch, agentdrill, agentcomply) |
| 3 — Protocol/enterprise | Generic **MCP clients** (incl. Claude Desktop) · enterprise platforms (Copilot Studio, Agentforce, Bedrock agents) | MCP-layer tools are harness-agnostic by construction; enterprise platforms via standards, v2.x |

This tool's specific per-tier minimums: see the [per-tool compatibility table](../00-harness-compatibility.md#per-tool-compatibility-requirements).

## 3. Explicit non-requirements
- No credential creation/rotation tooling (the org's IdP stays the source of truth; we broker, never mint long-lived secrets).
- No browser/session secret capture of any kind.
- No enterprise directory sync in v1 (backends are pluggable later).

## 4. Standards it must meet
RFC 8693 token exchange (downscoped issuance); RFC 8707 audience binding; RFC 9700 security BCP; the stdio-credential pattern contributed upstream to MCP ext-auth (standards authorship = owning the default implementation).

## 5. Fit in the ecosystem
The hands on the keys, below every harness: agentgate uses its tokens, agentpolicy approves issuances/upgrades, agenthalt triggers revocations, agentkernel/agentseatbelt block raw-secret reads as defense-in-depth, agentdrill measures kill times, agentcomply reports the credential lifecycle.

## 6. Success metrics (outcome-level)
- Kill-time: alert-to-dead-credential ≤1s, verified continuously in CI (not just at launch).
- Zero usable secrets in agent context across all PRD 09 attack packs — permanent invariant.
- Backend coverage: % of customer credentials that live in supported backends vs. still in env (the migration funnel).

## 7. Open questions
- Egress-injection granularity for non-MCP tools (arbitrary CLIs with env-file expectations) — where does virtualization end?
- Shared-session semantics: multiple agents, one user credential — inherit, split, or deny?

---

## Trace: every source line → where it lives now

| Source (above) | Now lives in | Notes |
|---|---|---|
| §1 Why (4 points) | [PRD 01](01-why.md) failure modes C1–C4 | Expanded with 2026 evidence (GitGuardian, Aembit MCP Gateway, WIMSE/AIMS) |
| §2 R1–R7 | [PRD 05](05-features.md) **R1–R7** (all P0) | Identical semantics; acceptance criteria expanded |
| §2 R8 (vault/1P/K8s backends) | [PRD 05](05-features.md) **R10** (P1) | Renumbered; conformance-gated contract added |
| §2 R9 (step-up) | [PRD 05](05-features.md) **R9** (P0) | **Promoted to v0.1.0** — it is cheap once agentpolicy `ask` exists and it is the EU-AI-Act-14 story |
| §2 R10 (stdio virtualization) | [PRD 05](05-features.md) **R8** (P0, flagship) | **Promoted to v0.1.0** — the unowned row #8 is the reason the product exists |
| §2 R11 (SPIFFE) | [PRD 05](05-features.md) **R12** (P1) | Renumbered; WIMSE/AIMS alignment added |
| §2 R12 (credential health reports) | [PRD 05](05-features.md) **R18** (P1, `agentkeys posture`) | Renumbered and productized |
| Harness Compatibility block | [PRD 19](19-harness-compatibility.md) + [PRD 16](16-adapters-and-integration.md) | Below-the-harness model + per-harness recipes |
| §3 Non-requirements | [PRD 14](14-non-goals.md) NG-1..NG-2, PF-1 | Verbatim in spirit; expanded with disambiguations |
| §4 Standards | [PRD 20](20-standards-and-claims.md) §1–§3 | Expanded: RFC 9728/9068/9449, MCP best practices, conformance gates, the contribution plan |
| §5 Ecosystem fit | [PRD 02](02-architecture.md) §7 | Expanded into the composition table |
| §6 Success metrics | [PRD 07](07-success-metrics.md) | Kill-time, zero-secret invariant, migration funnel — all three kept as the headline set |
| §7 Open question 1 (egress granularity) | Answered: [PRD 02](02-architecture.md) §4 + [PRD 16](16-adapters-and-integration.md) §3 | Three drivers with a hard boundary: virtualization ends where a process we do not mediate reads a file we do not control — and we say so |
| §7 Open question 2 (shared-session) | Answered: [PRD 11](11-decisions.md) **D-17** | Deny ambient; explicit, monotonically-narrowing delegation at R11; separate revoke domains |
