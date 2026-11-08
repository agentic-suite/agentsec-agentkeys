# PRD 10 — Feature Parity

**BLUF:** agentkeys does not try to out-feature the enterprise brokers; it closes the **three rows in the
coverage map that nobody owns** — **stdio MCP credential virtualization**, a **published, reproducible
`revoke` ≤1s**, and **public zero-usable-secret evidence** — and it does so as the only **OSS, local-first,
below-the-harness** broker. On the seven capabilities that matter for the agent's *own* credential surface
(never-in-context, JIT short-lived creds, audience binding, tool scope, session binding, unified revoke,
lifecycle audit) it **matches or leads** the field. On the enterprise control plane — HA/fleet, backend
breadth, conditional access, compliance letters, SIEM — it is deliberately **behind today and honest about
it**. The matrix below is our assessment from public material, not an audit.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Method, legend, and honesty rule

- **Ratings** are our read of each vendor's public docs/positioning as of **2026**, *not* a procurement or a
  third-party audit. Where a product plausibly does something, we say so; where we are unsure, the note says
  "unclear".
- **Labels** follow [PRD 20](20-standards-and-claims.md): *documented · conformance · field-tested ·
  verified*. No cell claims more than its evidence.
- **Scope rule:** a capability is only rated for what the product ships **for agents**, not for its general
  secrets-manager or gateway feature set.

| Rating | Means |
|---|---|
| **●●●** | Strong / first-class — a stated capability or a clear product differentiator |
| **●●○** | Substantial — covered, but scoped, indirect, or not its primary model |
| **●○○** | Peripheral — incidental coverage, narrow, or single-harness |
| **○○○** | None / not part of this product's model |

## 2. Capability key

| # | Capability | What "good" means | Anchor |
|---|---|---|---|
| C1 | **Never-in-context** | Real secret is never rendered into agent context/args/logs; agent holds a reference/placeholder | R1 |
| C2 | **JIT short-lived creds** | Credential minted at moment of use, minutes-scale TTL, no standing secret | R3 |
| C3 | **Audience binding** | Token bound to one server/resource (RFC 8707-shaped) | R3 |
| C4 | **Tool scope** | Token bound to one tool/operation | R3 |
| C5 | **Session binding** | Token tied to one conversation/session; dies with it | R3 |
| C6 | **stdio MCP virtualization** | Local stdio MCP server gets a brokered credential, **not** a config/env secret | R8 (flagship) |
| C7 | **Unified revoke ≤1s** | One command/one click kills all of an agent's access, immediately | R4 |
| C8 | **Step-up human gate** | Higher-class scope requires an explicit approval decision | R9 |
| C9 | **Lifecycle audit / OTel events** | Issuance/use/revoke emitted, joinable to the session trace | R6 |
| C10 | **Pluggable backends** | Multiple storage backends behind one contract | R5, E9 |
| C11 | **Local-first / offline** | Runs with no cloud account; works air-gapped | E4 |
| C12 | **OSS** | OSI-approved open source, self-hostable | — |
| C13 | **Published kill-time / zero-secret evidence** | A public, re-runnable benchmark of the two claims | R4, R1 |
| C14 | **Policy portability** | Policy is delegated/interoperable, not a new vendor lock-in | R9 |
| C15 | **Secret-hygiene migration + posture** | Finds candidate secrets where agents read them; guided migration to backends; continuous posture report | R17, R18 |

## 3. Gap-closure matrix

Read the two competitor tables together with **table C** (agentkeys + verdict). They are split only for
width; the row order is identical.

### 3a. Commercial enterprise brokers

| # | Aembit | Entra Agent ID | 1Password Credential Broker | Doppler | Infisical Agent Vault | HashiCorp Vault |
|---|---|---|---|---|---|---|
| C1 | ●●● never-in-context JIT | ●●○ token, not reference | ●●● never returns values | ●●○ agents request secrets | ●●● placeholder/proxy | ●○○ client receives secret |
| C2 | ●●● | ●●● short-lived tokens | ●●● per-job brokering | ●●● dynamic secrets | ●●● dynamic secrets | ●●● leases |
| C3 | ●●○ scoped, not RFC-shaped | ●●○ `aud` in token | ●●○ per-job scope | ●●○ agent-scoped OIDC | ●●○ path/method rules | ●○○ policy, not audience |
| C4 | ●●● per-tool MCP filtering | ●●○ app roles/scopes | ●●○ per-job | ●●○ | ●●○ path/method | ●●○ policy paths |
| C5 | ●●○ | ●●○ | ●●○ | ●●○ | ●○○ per-request | ●○○ leases |
| C6 | ●○○ gateway/HTTP-shaped | ○○○ | ●○○ sandbox placeholders | ●○○ MCP server | ●○○ HTTP proxy | ○○○ |
| C7 | ●●○ one-click kill, no ≤1s proof | ●●○ centralized revoke | ●●○ runtime revoke | ●○○ revoke account | ●○○ no cascade | ●●○ lease revoke |
| C8 | ●●○ conditional access | ●●● CA + approvals | ●●○ approval | ●○○ | ●○○ | ●●○ control groups |
| C9 | ●●● SIEM export | ●●● Defender XDR | ●●○ | ●●○ | ●●○ | ●●● audit devices |
| C10 | ●●○ integrations | ●○○ MS identity | ●●○ own + brokering | ●●○ own platform | ●●○ own platform | ●●● plugin ecosystem |
| C11 | ●○○ tenant plane | ●○○ cloud | ●○○ commercial | ●○○ | ●●○ self-host | ●●○ self-host, heavy |
| C12 | ○○○ | ○○○ | ○○○ | ○○○ | ●●○ open-core | ●○○ source-available (BUSL) |
| C13 | ○○○ claims, no re-run | ○○○ | ○○○ | ○○○ | ○○○ | ○○○ |
| C14 | ●●○ vendor policy | ●●○ MS conditional access | ●○○ | ●○○ | ●○○ | ●●○ HCL policy |
| C15 | ●○○ NHI discovery, not dev-env migration | ○○○ | ●●○ developer-secrets guides, env loading | ●●○ `.env` import, change requests | ●●○ `.env` import | ●●○ Vault Radar (separate product) |

### 3b. Network gateways, OSS, and platform-native

| # | Cloudflare AI Gateway | Solo `agentgateway` STS | OSS (iron-proxy / secretless-ai / Leash) | Platform-native (Claude Code hooks, Cursor, Codex, Copilot) |
|---|---|---|---|---|
| C1 | ●○○ gateway, not a secret model | ●●○ session → token | ●●● server-side inject / keychain | ●○○ hooks, single-harness |
| C2 | ○○○ | ●●● STS exchange | ●●○ varies by project | ●○○ where configured |
| C3 | ○○○ | ●●● RFC 8693 | ●○○ default-deny egress | ○○○ |
| C4 | ○○○ | ●●○ scope in exchange | ●○○ | ●○○ |
| C5 | ○○○ | ●●○ session credential | ●○○ | ○○○ |
| C6 | ○○○ | ○○○ network egress only | ●○○ secretless-ai / stdio bridge | ●○○ static env |
| C7 | ○○○ | ●●○ one-place revoke | ●○○ | ●○○ |
| C8 | ○○○ | ○○○ | ○○○ | ●○○ harness prompts |
| C9 | ●●○ AI-call observability | ●●○ gateway logs | ●○○ | ●○○ |
| C10 | ●○○ | ●●○ gateway backends | ●●○ keychain / 1Password | ○○○ |
| C11 | ●○○ cloud | ●●○ self-host | ●●● local | ●●● local |
| C12 | ●○○ partial | ●●○ agentgateway OSS | ●●● | ○○○ |
| C13 | ○○○ | ○○○ | ●○○ tests, not an evidence pack | ○○○ |
| C14 | ●○○ | ●●○ standards-based | ●○○ | ●○○ |
| C15 | ○○○ | ○○○ | ●●○ gitleaks/trufflehog detect — but don't migrate or broker | ○○○ |

### 3c. agentkeys — parity and the gap verdict

| # | agentkeys **v0.1.0** | agentkeys **roadmap** (R10–R16) | Gap verdict |
|---|---|---|---|
| C1 | ●●● Apache-2.0 reference model | ●●● | Match the best (1Password, Infisical, Aembit); OSS + below-harness is the differentiator |
| C2 | ●●● TTL floor/ceiling per class | ●●● | Table stakes — we match the leaders |
| C3 | ●●● RFC 8707, conformance-gated | ●●● | **Lead** on standards-shaped binding in a local OSS broker (Solo is the peer, on network egress only) |
| C4 | ●●● one tool per token | ●●● | Peer of Aembit's per-tool filtering, in OSS |
| C5 | ●●● session-bound + revoke cascade | ●●● | **Lead** — a single session-binding model across all egress points |
| C6 | ●●● **flagship**, documented boundary | ●●● | **We are alone** — coverage row #8 |
| C7 | ●●● `revoke` ≤1s, replay-verified in CI | ●●● | **Lead** on published ≤1s; Aembit is the capability peer (no re-runnable proof) |
| C8 | ●●● via agentpolicy `ask` | ●●● | Peer of Entra Conditional Access, but **delegated/portable** |
| C9 | ●●● agentwatch schema + hash chain | ●●● | Peer of Aembit/Vault; native OTel GenAI semconv |
| C10 | ●●○ **keychain + credential file only** | ●●● R10 cloud/enterprise backends | **Behind** Vault's ecosystem today — honestly labeled |
| C11 | ●●● air-gapped, no account | ●●● | **Lead** with OSS + platform-native |
| C12 | ●●● Apache-2.0 | ●●● | **Lead** (Apache-2.0 vs Infisical open-core / Vault BUSL) |
| C13 | ●●● attack packs + kill-time benchmark | ●●● | **We are alone** — nobody else publishes a re-runnable proof |
| C14 | ●●○ delegates to agentpolicy (Cedar/AuthZEN) | ●●● | We **refuse** to be a policy engine, by design ([PRD 14](14-non-goals.md)) |
| C15 | ●●● scan → migrate → broker in one tool (R17); posture next (R18) | ●●● | **Lead** — everyone else detects or stores; nobody walks you out of `.env` into a brokered reference |

## 4. Where we lead

- **stdio MCP credential virtualization (C6).** The MCP spec tells stdio servers to read credentials from
  the environment; no commercial or OSS product covers it (coverage-map **row #8**). agentkeys does, with a
  documented process-boundary limit ([PRD 06](06-security-baseline.md) §4).
- **Published kill-time + zero-secret evidence (C13).** A public, re-runnable benchmark and the context-dump
  attack pack, both CI-gated — the thing nobody publishes.
- **The OSS + local-first + below-the-harness combination (C11, C12).** Free, five-minute, air-gapped, and
  structurally *below* every harness (env + header interception generalizes).
- **Session binding as one model (C5).** Every egress point (env, header, exchange) shares one session-bound
  binding and one revoke cascade.
- **Standards-shaped binding in a local broker (C3).** RFC 8693 / RFC 8707 in a tool you `pip install`.
- **Secret-hygiene migration + posture (C15).** Detection tools (gitleaks, trufflehog) find secrets and
  stop; vault vendors store them and stop. agentkeys is the only one that walks the credential **out of
  the agent's world** — detect → migrate → broker → posture — as one guided flow (R17/R18).

## 5. Where we are behind (honest)

| Behind | Who leads | Reality | When |
|---|---|---|---|
| Enterprise control plane, HA/fleet, multi-tenant | Aembit, Entra Agent ID | v0.1.0 is a single-user local broker + local store | **R11**, v0.2.0 |
| Backend breadth | Vault, 1Password, Doppler, Infisical | We ship **OS keychain + credential file** only | **R10**, v0.1.x–v0.2.0 |
| Conditional access / posture (geo, time, device) | Aembit, Entra | We gate on step-up approval, not posture signals | roadmap |
| Compliance certifications (ISO 27001, SOC 2) | Aembit, 1Password and other vendors | We **map** to frameworks; we are **not certified** | roadmap (v1.x) |
| Enterprise integrations / SIEM at scale | Aembit, Vault, Entra | We emit events + a local ledger; sink adapters are early | v0.1.x+ |
| Sender-constrained tokens (DPoP) | Ping and others named the gap | Bearer tokens until **R14** | v0.3.0 |
| GUI | Most commercial products | CLI + local ledger only | roadmap |
| Windows | Broad | macOS + Linux first | roadmap (measure demand) |
| Fleet-scale throughput | Enterprise planes | Single-process local broker | **R11** |

## 6. Where we do not compete

agentkeys deliberately refuses the following lanes; competing there would blur the decision boundary and
break [PRD 14](14-non-goals.md):

- **Not a secrets manager / vault.** Backends store; we broker. No migration of your secrets into us.
- **Not an identity provider.** We consume identity (WIMSE/SPIFFE at R12); we do not issue it.
- **Not a policy engine.** agentpolicy decides; we ask and enforce the answer.
- **Not an enforcer / sandbox.** agentkernel/agentseatbelt enforce; we emit the event.
- **Not an LLM gateway / observability platform.** Cloudflare and Solo keep that lane.
- **Not browser/session credential capture.** Permanently refused (anti-feature).
- **Not a compliance letters vendor.** We supply evidence; the auditor certifies.
- **No long-lived secret minting or rotation.** The IdP is the source of truth.

## 7. How to read this without over-claiming

- Every **agentkeys v0.1.0** ●●● above is a *documented* or *conformance* claim today; *field-tested* status
  arrives only via the hand-maintained field-test report ([PRD 21](21-evidence-register-and-method.md)).
- Competitor ratings are **our assessment**, not their claims; treat them as a starting point for a
  conversation, not a scoreboard.
- Row #8 (stdio) and row #7 (unified revoke) are the *reason the product exists*; the matrix exists to keep
  us honest about everything **not** in those rows.
