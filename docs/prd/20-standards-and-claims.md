# PRD 20 — Standards & Claims

**BLUF:** For a credential broker, **standards compliance is not documentation — it is the product.** A
broker that invents its own token format is a lock-in; a broker that speaks **RFC 8693 / RFC 8707 / RFC
9700 / RFC 9728**, the **MCP authorization** model, and **SPIFFE/WIMSE** identity interoperates with the
IdP, the gateway, and the resource server the customer already runs. agentkeys **implements** the OAuth
token-exchange and audience-binding standards, **aligns to** the agent-identity work at the IETF
(**WIMSE/AIMS**), and is built to be **verifiably compliant** (E13): every implemented standard has a
conformance suite that gates the release, and every claim carries a label no higher than its evidence
(*documented · conformance · field-tested · verified*). This document is the map; the conformance report is
the proof.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Standards we IMPLEMENT (with a conformance gate)

| Standard | What it governs for us | How agentkeys implements it | Conformance |
|---|---|---|---|
| **RFC 8693** — OAuth 2.0 Token Exchange | Downscoped, per-target issuance from a session credential (the core mint) | The exchange injector requests a narrow token per `(audience, tool, session)`; `subject_token` = session credential, `audience`/`resource` = target, `scope` = the tool's operation | `agentkeys conformance rfc8693` + `tests/conformance/test_rfc8693.py` |
| **RFC 8707** — Resource Indicators | **Audience binding** (kills confused-deputy replay across servers) | Every issued token carries exactly one `resource`/`aud`; the egress injector refuses to widen it | `tests/conformance/test_rfc8707.py` |
| **RFC 9700** — OAuth 2.0 Security BCP | Baseline hygiene for every flow we broker | PKCE (7636) where a code flow is involved; exact issuer identification; exact redirect/audience matching; no implicit; sender-constraining (DPoP) as R14 | `tests/conformance/test_rfc9700.py` |
| **RFC 9728** — Protected Resource Metadata | Resource discovery for authorization | The HTTP egress injector honors `<resource>/.well-known/oauth-protected-resource` when present | `tests/conformance/test_rfc9728.py` |
| **RFC 9068** — JWT Profile for OAuth 2.0 Access Tokens | Interop shape of the tokens we mint | Minted access tokens are profiled JWTs (`typ: at+jwt`) with the binding claims | `tests/conformance/test_rfc9068.py` |
| **RFC 7636** — PKCE | Authorization-code protection | Required for any interactive flow a backend adapter drives | `tests/conformance/test_pkce.py` |
| **RFC 9449** — DPoP (sender-constrained tokens) | Proof-of-possession so a stolen token string is useless | **R14 (v0.3.0)** — enumerated now, not claimed as done | scheduled |
| **MCP Authorization** (spec 2025-06-18 / 2025-11-25) | Authorization for **HTTP** MCP egress | The HTTP egress injector acts as the resource-server-side broker: OAuth 2.1 model, RFC 8707 audience, RFC 9728 metadata, 401 step-up challenge | `tests/conformance/test_mcp_auth.py` |
| **MCP Security Best Practices** | Anti-patterns (esp. **no token passthrough**) | **E14**: the broker never forwards a client token upstream; it mints a scoped credential for the target | `tests/conformance/test_no_token_passthrough.py` |
| **OTel GenAI semantic conventions** | Vendor-neutral telemetry for agent/tool spans | Lifecycle events ride `execute_tool` / agent spans with `gen_ai.tool.name`, `gen_ai.agent.id` | `tests/conformance/test_otel_semconv.py` |

## 2. Standards we ALIGN TO (roadmap, labeled honestly)

| Standard | Why | Status in agentkeys |
|---|---|---|
| **IETF WIMSE / "AIMS" — AI Agent Authentication & Authorization** (`draft-klrc-aiagent-auth`; OpenAI · Okta · AWS · Ping · Zscaler) | Names the exact shape: one agent workload **identity**, a **short-lived credential**, OAuth token **exchange** for delegated authority | Design-aligned today; **R12 (v0.2.0)** implements agent workload identity |
| **SPIFFE / SPIRE** (SPIFFE IDs, JWT/X.509/WIT SVIDs) | Workload identity as the actor credential, carried as the RFC 8693 `actor_token` | **R12**; SPIFFE IDs accepted as WIMSE identifiers |
| **ID-JAG** (`draft-ietf-oauth-identity-assertion-authz-grant`) | Cross-app delegated authorization without pre-shared secrets | Adapter slated post-v0.1.0 |
| **Transaction Tokens** (`draft-ietf-oauth-transaction-tokens`) | Propagate identity/authorization unchanged across a call tree | Tracked for R11 (fleet mode) |
| **OAuth 2.1** (draft) | Consolidated baseline | Followed; conformance inherits RFC 9700 |
| **AuthZEN** | PDP interop (we ask agentpolicy; a PEP could ask a PDP) | Adapter support slated |
| **Cedar** | The policy language for step-up decisions (via agentpolicy) | Consumed, not reimplemented |
| **CyberArk Secretless Broker pattern** | Precedent for injecting auth outside the app | Adopted conceptually (never-in-context, protocol-aware injection) |

### 2a. Why bearer until R14 — and what DPoP changes

v0.1.0 issues **bearer** tokens. That is a deliberate, labeled choice — not an oversight:

- **Why bearer is acceptable *here*** — our tokens are short-lived (per-class TTL with ceilings),
  audience-bound (RFC 8707), tool-scoped, **session-bound**, and **single-use per call**; and the secret
  itself never sits in the agent's context, so the theft window is not "the agent's whole session" but the
  egress path of one call. A stolen token is already: wrong for any other audience, wrong for any other
  tool, dead at session end, dead after one use, and dead at TTL — typically minutes.
- **Where proof-of-possession matters most** — where a token string can be observed *in transit or by the
  target process*: the HTTP header driver against third-party APIs, and long-lived sessions with
  exfiltration-prone tools. It matters least for the env-virtualization driver, where the token crosses a
  process boundary we control on both ends.
- **Which targets can realistically support it** — our own stdio wrapper ↔ broker hop (we own both
  sides: the first candidate), then egress to any downstream that advertises RFC 9449; enterprise APIs
  are adopting DPoP faster than mTLS-for-everything.
- **What changes when R14 lands** — DPoP adds **proof-of-possession**: a replay of the *same token string
  against the same audience within its TTL* stops working too, because the replaying client cannot
  produce a valid proof bound to its own key. Sequencing: ship the wrapper↔broker hop first (both ends
  ours, conformance-testable), then third-party egress as targets support it. Until then, this row stays
  *scheduled* and must not be implied as done.

## 3. The stdio-credential **MCP ext-auth contribution** (standards authorship = owning the default)

The MCP authorization chapter covers **HTTP** transport and tells **stdio** servers to read credentials from
the **environment** — which is why a broad, long-lived secret ends up in an agent-readable config. That is
coverage-map **row #8: nobody**. agentkeys closes it in code (R8) **and** proposes the pattern upstream: a
documented, transport-neutral way for a local server to receive a **broker-scoped, short-lived** credential
at call time instead of a static env value — with **no token passthrough** and an explicit audience. The
contribution is prepared in-repo (reference pattern + fixtures + a threat-model appendix) so it can be filed
to MCP `ext-auth` with reproducible evidence. Owning the default implementation of the pattern we propose is
the strategy, not a side quest ([moat: standards authorship]).

### 3a. The contribution plan (concrete)

| Piece | Content |
|---|---|
| **Problem statement we file** | "stdio servers are told to read credentials from their environment. In agent-driven hosts, that environment is agent-readable config: the credential is static, unscoped to any audience, and unrevocable — and token passthrough is already named an anti-pattern by the security best practices. There is no standard way for a local server to receive a short-lived, audience-bound credential at call time." |
| **Minimal pattern we propose** | (1) a **placeholder** (reference) instead of a literal secret in server config; (2) call-time **broker-mediated substitution** at a process boundary, with the issued credential carrying **audience + tool/session claims** (RFC 8693/8707 shapes); (3) an explicit **no-passthrough** rule for client tokens; (4) a named **process-boundary requirement** with the honest co-located-runtime limit stated in the threat-model appendix. |
| **What we deliberately do NOT standardize yet** | Backend discovery or vault vendors (backend-specific), reputation/attestation (R15, separate), the ledger/event format (agentwatch owns it), policy language (Cedar/agentpolicy own it). Standardize the seam, not the ecosystem. |
| **Reference implementation** | agentkeys R8 + the stdio fixtures (SC-12/SC-13) + this threat appendix — the pattern in code and the pattern proposed are the same pattern. |
| **Filing path** | MCP `ext-auth` issue → short problem doc → draft pattern doc + fixtures link → maintainer feedback loop. |
| **Acceptance (our gate, [PRD 09 §6](09-roadmap.md))** | Issue filed with reproducible evidence by v0.3.0; merged, **or** the maintainer response recorded verbatim in the docs. A rejected-with-reasons contribution is still standards work; silence is not. |

### 3b. The IETF track (WIMSE / AIMS)

The **AI Agent Authentication and Authorization (AIMS)** draft — co-authored across OpenAI, Okta, AWS,
Ping, Zscaler, Defakto — names exactly our shape: one agent workload **identity** (WIMSE/SPIFFE ID), a
**short-lived credential**, and **OAuth token exchange** for delegated authority. That is a second
authorship lane, and it has a concrete path:

1. **Implement, then speak.** R12 implements the actor side (SPIFFE SVID as the RFC 8693 `actor_token`,
   joined to `gen_ai.agent.id`). An implementer with conformance results and a public benchmark speaks
   with evidence at WIMSE; a vendor deck does not.
2. **Contribute the local-broker use case.** The AIMS material is server/enterprise-shaped today; the
   **developer-laptop broker** (stdio, keychain, no IdP) is a use case the drafts under-specify. We file
   the gap as an issue/segment contribution with our fixtures — the same "own the default implementation"
   play as ext-auth, smaller stakes.
3. **Acceptance:** an issue/contribution on file with reproducible evidence by the R12 release; the
   working-group response recorded verbatim either way. We do **not** claim "IETF compliance" — drafts are
   drafts; we say *aligned* (§2), and the label rules in §6 apply.

## 4. Compliance framework mappings (what we cover → which risk)

| Framework | Item | agentkeys control |
|---|---|---|
| **OWASP LLM Top 10 2025** | **LLM02** Sensitive Information Disclosure | Never-in-context invariant (R1); redaction-by-default (E5); egress-only injection (R2) |
| | **LLM06** Excessive Agency | Per-tool/tool-scoped tokens (R3); step-up for prod scope (R9); blast-radius budgets (R13) |
| | **LLM05** Improper Output Handling | Agent/tool text is data, never a credential path; evasion detection (R7) |
| | **LLM01** Prompt Injection | **Architectural mitigation, not detection** — keep secrets out of reach so injection cannot win |
| **OWASP Agentic AI Top 10** (draft) | Identity confusion | One audience per token (RFC 8707); session binding (R3); agent identity via WIMSE (R12) |
| | Excessive agency | Least-scope issuance; step-up (R9); budgets (R13) |
| | Memory poisoning / data exfil | Reference-only context (R1); egress taint later (R16) |
| **NIST AI RMF + NIST AI 600-1** | "Manage"/"Govern" outcomes | Credential-lifecycle ledger (R6) as governance evidence |
| **NIST SP 800-207** (Zero Trust) | No implicit trust; per-request authorization | Per-request token mint with runtime bindings; no standing credential |
| **MITRE ATLAS** | Credential-access / exfiltration techniques | Lifecycle events tagged for ATLAS-style mapping; incident register feeds back |
| **ISO/IEC 42001 / ISO 27001** | AI management system / infosec controls | Controls-mapping appendix; supplier/credential controls |
| **EU AI Act Art. 14** | Effective human oversight | Step-up approvals (R9) + reconstructable decisions (R6) — *effective*, not theatrical |
| **CSA NHI guidance** | Non-human identity governance | Agent-as-NHI with own identity, scoped creds, attribution (R3/R6/R12) |
| **OWASP ASVS L2 / SAMM** | Our own application security / secure SDLC | Target for the broker's own code; SAMM for process |

### 4a. Deep mappings: EU AI Act Art. 14 and NIST SP 800-207

Two frameworks deserve more than a table row, because they map to what agentkeys *is*, not just what it
covers:

**EU AI Act Article 14 (human oversight of high-risk AI systems)** — oversight must be *effective*, not
theatrical. agentkeys makes it enforceable at the credential layer:

| Art. 14 obligation | agentkeys control |
|---|---|
| Oversight must be able to **prevent or halt** a risky action during operation | `revoke` ≤1s (R4) — the overseer's interrupt is a *provably dead credential*, not a polite request; agenthalt composes it into a full stop |
| **Authorization of a consequential step** by an overseer before it proceeds | Step-up issuance (R9): prod-class scope is *impossible* to mint without an approving human decision; timeout = deny |
| Safe behavior when the **overseer is unavailable** | Fail-closed everywhere (E4) + timeout = deny — no ambient authority flows in the absence of a human |
| **Logging of oversight activity** (demonstrable oversight) | The hash-chained lifecycle ledger (R6): every approval, issuance, use, and revoke attributed to a principal, joined to the session trace |

**NIST SP 800-207 (Zero Trust Architecture)** — the broker is zero trust applied to the agent's
credentials, per-request:

| 800-207 tenet | agentkeys implementation |
|---|---|
| **No implicit trust** based on network location or asset ownership | No standing credential anywhere: every use re-resolves and re-mints through the broker, local or not |
| **Per-request access decisions**, least privilege, scoped | Per-call issuance bound to one audience, one tool, one session (R3) — the narrowest grant that completes the call |
| **Dynamic policy** with context consumed as part of the decision | Step-up (R9) consults agentpolicy per class/audience; policy is evaluated *at the moment of use*, not at session start |
| **Continuous verification** (never "authenticate once") | Short TTLs + single-use consumption + revoke epochs: trust expires by default and is re-established per call |
| **The resource itself enforces** (defense in depth) | Audience enforced **at our egress injector** even if the downstream fails to check (E14) — we do not rely on the target's diligence |

## 5. Our own reliability ladder (the product is a security product — it must be provable)

| Control | Why it is mandatory here | Milestone |
|---|---|---|
| `security.txt` + coordinated-disclosure policy | A security product without a vuln policy is dead on arrival with buyers | **v0.1.0** |
| **Signed releases (Sigstore) + SLSA provenance + pinned deps** | Plugin4Shell was a supply-chain attack on coding agents; ours must be clean | **v0.1.0** |
| **SBOM** (CycloneDX/SPDX) on every release | consumable by scanners | **v0.1.0** |
| **OpenSSF Scorecard** (A target) | public, third-party-read supply-chain posture | **v0.1.0** |
| **OSS-Fuzz** for parsers (reference grammar, MCP/JSON-RPC frames) | malformed input must not crash enforcement | v0.1.x |
| **CVE / CNA + published advisory flow** | responsible disclosure at scale | v0.1.x |
| **Reproducible benchmark** (context-dump + kill-time) | the claim must be independently re-runnable | **v0.1.0** |
| **CIS-benchmarked hardened deployment manifests** (when server mode lands) | buyers verify our own posture | R11 |
| **SOC 2 Type I → Type II**, ISO/IEC 27001 | enterprise procurement; start the evidence pipeline from day one | roadmap (v1.x) |
| **FIPS-mode operation** (OS-native crypto) | government buyers; claim *mode*, not our own module | roadmap |

## 6. Claims vocabulary (labels — never use a higher label than the evidence)

| Label | Means | Example |
|---|---|---|
| **documented** | written in this PRD set; no test yet | new P2 requirements |
| **conformance** | passes a spec/contract suite in CI | "implements RFC 8707 audience binding" |
| **field-tested** | verified by the hand-maintained field-test report | "install→first brokered call < 15 min" |
| **verified** | independently reproduced by a third party | "kill-time ≤1s, re-run by X" |

### 6a. Product claims vocabulary (what our words mean on a label)

These terms are *product claims*, and each has exactly one meaning. Marketing, READMEs, and release notes
may not use a stronger term than the evidence supports:

| Term | It means exactly this | Do not use it for |
|---|---|---|
| **brokered** | The credential was resolved by agentkeys from a backend and injected at egress; the agent held only a reference | A value merely stored in a vault, or `op run`-style env loading |
| **reference-only** | No secret bytes ever rendered into agent context/args/logs — verified by the context-dump pack | "We try not to log secrets" |
| **audience-bound** | The token is refused for any server other than its RFC 8707 target — conformance-tested | "Scoped" in a vague sense |
| **tool-scoped** | One tool/operation per token | API-wide or role-wide scope |
| **session-bound** | The token dies with the session — replay after session end fails | Tokens that merely "expire eventually" |
| **revocable ≤1s** | Measured end-to-end, replay-verified, **in CI** | A revoke *button* without a published number |
| **first-class recipe** | Named harness recipe shipped **and** its agentdrill pack green in CI | A config snippet we never tested |
| **lower-layer coverage** | The harness's hook surface is closed; we cover it at the process/network layer, honestly labeled | A first-class claim |
| **field-tested** | Recorded by hand in the hand-maintained field-test report from committed evidence | Anything a script wrote |
| **verified** | A third party reproduced our published benchmark | Our own re-run of our own benchmark |

## 7. Non-claims (what we explicitly do NOT assert)

- **Not** a compliance certification: we map to SOC 2 / ISO 42001 / EU AI Act; we are not certified (yet).
- **Not** an injection *detector*: we mitigate architecturally and never claim detection rates.
- **Not** a proof-of-possession system at v0.1.0: bearer tokens until DPoP (R14).
- **Not** protection from a process that shares the agent's readable runtime (documented boundary, PRD 06).
- **Not** an identity provider: we consume identity (WIMSE/SPIFFE at R12), we do not issue it.
- **Not** a vault: backends store; we broker.
