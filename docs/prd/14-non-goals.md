# PRD 14 — Non-goals

**BLUF:** A credential broker is defined as much by what it **refuses** to be as by what it builds. The
refusals fall into two piles. The first is permanent and security-shaped: agentkeys will **never** issue a
long-lived secret, capture browser/session credentials, put machine learning in the enforcement path,
invent a proprietary token format, or forward a client token upstream. The second is a **phase** boundary
for v0.1.0: no SSO/SCIM/multi-tenant, no cloud backends yet, no server/HA mode, no GUI, no Windows. Drawing
both lines loudly is the point — a broker that quietly grows into a vault, an IdP, a policy engine, or a
detector would betray the one property its users depend on: **the secret stays where it belongs and the
agent gets a reference.** This document exists so that "that is not us" is a written answer, not a debate.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## How to read this document

- **Security boundaries (permanent)** — a refusal that will not change in any release. Crossing it would
  break a security property, not just a roadmap ([PRD 06](06-security-baseline.md)).
- **Product boundaries (this phase)** — a scope limit for v0.1.0, with a stated later home and trigger
  ([PRD 11](11-decisions.md) deferred decisions; [PRD 03 §4](03-landscape.md)).
- **Disambiguations** — the one-line "that is somebody else's job" answers, each pointing at who owns it.
- Requirements and priorities referenced here are in [PRD 05](05-features.md); the frozen decisions that
  produce these refusals are in [PRD 11](11-decisions.md).

---

## 1. Security boundaries (permanent)

| # | Refusal | Why (the property it protects) | Where it is enforced |
|---|---|---|---|
| **NG-1** | **No long-lived secret issuance.** We never mint a standing API key, never rotate the org's secrets, never create a credential that outlives a session. | A long-lived secret we minted is exactly the static, over-scoped key this product exists to delete (D-02). | R3, E3; [PRD 11](11-decisions.md) D-02 |
| **NG-2** | **No browser/session credential capture.** We do not harvest cookies, session tokens, or logged-in browser state. | Capturing session material re-creates the credential-in-context failure mode and turns the broker into a session-stealer. | Permanent; E10 |
| **NG-3** | **No ML in the enforcement path.** No classifier, no anomaly score, no model decides whether a credential is issued or blocked. | Enforcement must be deterministic and fail closed; a probabilistic allow/deny is neither auditable nor safe (D-06). | E4, E10 |
| **NG-4** | **No proprietary token format.** Tokens and references use open, standard shapes (RFC 9068 JWT profile, RFC 8693 exchange, RFC 8707 audience); the reference grammar is public. | A bespoke format is lock-in and cannot be reliably verified by the customer's own tools (E13). | R3, E13; [PRD 20](20-standards-and-claims.md) |
| **NG-5** | **No token passthrough.** The broker never forwards a client-supplied token upstream; it mints an audience-bound credential for the target. | Passthrough is the MCP-named anti-pattern that dissolves the audience binding and enables confused-deputy replay (D-14). | E14; MCP security best practices |

**Note:** these five are not deferrals. DD-08…DD-10 in [PRD 11](11-decisions.md) mark three of them as
*permanent refusal* rather than "not yet", because the ecosystem boundary (not effort) is what forbids them.

## 2. Product boundaries (this phase — v0.1.0)

| # | Not in v0.1.0 | Reality today | Later home / trigger |
|---|---|---|---|
| **PF-1** | **SSO / SCIM / multi-tenant / directory sync** | Local single-user broker; we consume identity, we do not administer it | R11 (server/HA) → enterprise; enterprise deployment trigger ([PRD 11](11-decisions.md) DD-02/DD-03) |
| **PF-2** | **Cloud / enterprise secret backends** | v0.1.0 ships **OS keychain + credential file** only | **R10 (P1)** — 1Password, Vault, K8s Secrets, cloud SM, conformance-gated (D-16) |
| **PF-3** | **Server / HA / fleet broker mode** | Single-user local broker + local store + local ledger | **R11 (P1)**; fleet adoption trigger |
| **PF-4** | **A GUI / hosted dashboard** | CLI + local ledger + export | recurring operator demand for a viewer ([PRD 11](11-decisions.md) DD-04) |
| **PF-5** | **Windows support** | macOS + Linux first | roadmap, on measured demand ([PRD 03 §4](03-landscape.md), DD-01) |
| **PF-6** | **Compliance certifications** | Framework **mappings** only; no SOC 2 / ISO 27001 attestation | SOC 2 Type I→II roadmap ([PRD 20 §5](20-standards-and-claims.md)) |
| **PF-7** | **A full eBPF secret-blocking engine** | We emit the evasion **event**; blocking is the enforcer's job | agentkernel / agentseatbelt composition |
| **PF-8** | **Non-OAuth / legacy protocol brokerage** | Transports covered are env, HTTP header, and RFC 8693 exchange | new egress driver on demand (E7), conformance-gated |

These are honest gaps, labeled *documented*, never dressed as shipped. The v0.1.0 claim is deliberately
narrow: **complete local never-in-context credential lifecycle**, nothing upstream of it.

## 3. Disambiguations ("that is not us — it is them")

| If someone asks… | The honest answer | Who owns it |
|---|---|---|
| "Is this a **secrets vault**?" | No. A vault **stores**; agentkeys **brokers**. Your secrets stay in your backend; we resolve, downscope, inject, revoke. | 1Password / Vault / Doppler / Infisical / cloud SM (D-01) |
| "Is this an **identity provider**?" | No. We **consume** identity (workload identity at R12), we do not issue it or run a directory. | Your IdP; WIMSE/SPIFFE/SPIRE (R12) |
| "Is this a **policy engine**?" | No. We **ask** for a decision and enforce it; we never decide. A broker that holds secrets must not also decide access. | **agentpolicy** (Cedar), AuthZEN PDP (D-10) |
| "Is this an **injection detector**?" | No. We do not classify prompts or claim detection rates; we make injection **not worth it** by keeping secrets out of reach. | ML detectors / guardrails — a different category ([PRD 20 §7](20-standards-and-claims.md)) |
| "Is this a **SIEM / observability platform**?" | No. We emit **agentwatch-schema events** and a local ledger; the SIEM aggregates them. | **agentwatch** + your SIEM |
| "Is this an **enforcement engine**?" | No. We detect evasion and emit an event; where a block is composed, the **enforcer** blocks it and we record both. | **agentkernel / agentseatbelt** (R7, E10) |
| "Is this a **rotation product**?" | No. Rotation belongs to the IdP/secret manager; we make rotation **routine** (rotate without restart, CUJ-10). | Your IdP / secret manager |
| "Is this a **gateway / proxy**?" | Not only. A proxy sees network traffic; we also handle the local cases a proxy cannot (stdio env, a CLI's file) (D-05). | agentgate (MCP OAuth proxy, Wave 1) + enterprise gateways |
| "Is this a **kill switch for the whole machine**?" | Not by itself. We revoke **credential access** ≤1s; a system-wide halt is a separate control we compose with. | **agenthalt** (kill-switch) |

## 4. Anti-features we will refuse even if asked

These are requests that would breach a permanent boundary. They are refused by default, not scheduled:

- **"Inject the key into the agent for convenience."** — the convenience path *is* the bug we remove (R1).
- **"Give me an endpoint that returns the plaintext secret."** — no read-out path exists by design (D-01).
- **"Disable fail-closed for my dev box and keep it off in prod."** — fail-closed is not a convenience
  toggle; a misconfiguration denies (D-06).
- **"Trust this custom backend without the conformance suite."** — an unverified backend weakens
  fail-closed; it is rejected at load (E9).
- **"Let revocation go through policy so we have an audit trail."** — revocation is unconditional; the
  audit trail is the event, not a gate (D-07).
- **"Forward my client token upstream so the server sees the right user."** — passthrough is refused;
  delegation is expressed through the RFC 8693 exchange shape (D-14).

## 5. What this is not a license to under-build

The refusals above **raise** the bar on what we do build:

- Keeping secrets out of the broker's own database means our **never-in-context** invariant must hold for
  our store, our logs, and our exports — proven by the evidence scanner (R1, E5).
- Refusing to be the policy engine means the **step-up boundary** must be exact: we ask, we never decide
  (R9, [PRD 11](11-decisions.md) D-10).
- Refusing to store secrets means **fail-closed** is the entire safety net; the fault-injection matrix is
  not optional (E4).
- Refusing to be a detector means the **evasion event** and its honesty rule (name the gap when we cannot
  block) carry the weight (R7).

## 6. What we build instead

The boundaries are only useful because something concrete replaces each refused capability. A no without a
substitute is a gap; a no with a substitute is a decision.

| We refuse to be… | We build instead | Decision |
|---|---|---|
| A **vault** | A broker that points at *your* backend and never stores plaintext | [D-01](11-decisions.md) |
| A **long-lived issuer** | Short-lived, audience/tool/session-bound tokens minted at use | D-02 |
| A **policy engine** | A **request** to agentpolicy for a decision we then enforce | D-10 |
| An **injection detector** | An **architectural** mitigation — keep secrets out of reach so injection is not worth it | D-01, [PRD 06 §6](06-security-baseline.md) |
| A **SIEM** | agentwatch-schema lifecycle events + a local hash-chained ledger + export | D-09 |
| An **enforcement engine** | Evasion **events**, plus **composition** with agentkernel/agentseatbelt | R7 |
| A **per-harness plugin** | Below-the-harness egress drivers (env, header, exchange) | D-03, D-05 |
| A **transparent MITM proxy** | Three narrow, contract-tested egress drivers | D-05 |
| An **SSO/IdP** | A consumer of workload identity (R12, later) | [PRD 20 §2](20-standards-and-claims.md) |

## 7. Boundaries inside our own codebase

The refusals also constrain what we build for ourselves — we do not grow a general-purpose platform:

- **Not a general-purpose secrets SDK.** The reference/issuance contract is scoped to brokering; it is not
  a library for arbitrary secret storage, retrieval, or distribution (E1).
- **Not a cryptographic module provider.** We use OS-native crypto and standard shapes; FIPS-mode (later)
  claims *mode*, never a home-grown module ([PRD 20 §5](20-standards-and-claims.md)).
- **Not a full authorization framework.** We **request** a decision and **enforce** it; we do not host
  policies, roles, or attributes (D-10).
- **Not a general egress firewall.** We **inject credentials** at egress; filtering all traffic is a
  different control (the enforcer / agentgateway).
- **Not a replacement for the harness sandbox.** We stay below the harness; the harness's isolation and the
  enforcer's blocking remain separate layers ([PRD 06 §3](06-security-baseline.md)).

## 8. Related documents

- What those decisions cost and buy: [PRD 11](11-decisions.md).
- The invariants and non-claims that back the refusals: [PRD 06](06-security-baseline.md) §6.
- The feature set that *is* in scope: [PRD 05](05-features.md).
- The scenarios that will prove the in-scope behavior: [PRD 17](17-scenarios.md).
- How we label claims so nothing here is over-claimed: [PRD 20 §6](20-standards-and-claims.md),
  [PRD 21](21-evidence-register-and-method.md).
