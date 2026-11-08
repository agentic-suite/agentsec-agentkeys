# PRD 01 — Why

**BLUF:** Every material agent-security control eventually reduces to one question about the credentials
the agent can reach. An agent with a static, long-lived, over-scoped secret in its environment is one
prompt-injection away from handing over the crown jewels, and when it does, the fix is a quarter-long
rotation. The landscape agrees on the answer — capability-scoped, session-bound, short-lived credentials
injected at egress, with instant revocation — and **almost nobody ships it**: revocation is the weakest
capability across the whole market (coverage map row #7), and **local stdio MCP credential handling is
covered by nobody at all (row #8)**. agentkeys is the small, local-first, below-the-harness broker that
closes both and makes "the agent leaked its key" a one-second command.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## The problem in one paragraph

A credential is only safe if the agent can *use* it without ever *holding* it, and if a human can make it
*stop working* the instant something goes wrong. Today's default gives the agent the opposite: a literal
secret pasted into `mcp.json`, a `.env`, an environment variable, or a config file — long-lived, broadly
scoped, with no audience binding and no kill switch. A prompt injection that reads the environment wins
permanently. When the team learns the key leaked, revocation means rotating it wherever it is used, which
means finding every place it is used, which means **a quarter of work**. The audience for this problem is
everyone who has given an agent a real credential and then tried to bound the blast radius: credentials
are the one control where "we'll clean it up later" is the whole problem. **The fix is structural, not
detective**: keep the secret out of the agent's reach, mint a narrow token at the moment of use, and make
revocation a primitive.

## Four failure modes, with evidence

| # | Failure mode | What happens today | Evidence | Consequence |
|---|---|---|---|---|
| **C1** | **The secret lives in the context** | Credentials are pasted into `mcp.json`, `.env`, environment variables, and config files; they live in the same readable runtime as the agent and its model context | Anthropic threat-intel (Sept 2026) documented in-the-wild prompt-injection exfiltrating **production API keys**; MCP tool-poisoning/rug-pull incidents; GitGuardian's *State of Secrets Sprawl 2026* found **28.65M hardcoded secrets** added to public GitHub in 2025 (+34% YoY) with **AI-service credentials the fastest-growing class** | One injection reads the environment and steals everything the agent can reach — permanently |
| **C2** | **There is no revocation** | Central revocation exists commercially only in Aembit and Entra Agent ID; everywhere else, "revoke the agent" means finding and rotating every credential it can touch | Coverage map row #7: commercial `●●○`, OSS `●○○` (single-maintainer experiments — iron-proxy, secretless-ai, Leash) | Incident response is a **rotation project**, not a command; agents stay dangerous while the cleanup runs |
| **C3** | **Credentials are standing and unbound** | A long-lived token has no audience, no tool scope, and no session life; it is accepted anywhere it is presented, and it outlives the task that needed it | RFC 8707 (resource indicators) and RFC 8693 (token exchange/downscoping) exist precisely to fix this; MCP security best practices name **token passthrough** an anti-pattern | Confused-deputy and replay: a token meant for one server is used against another; a hijacked session keeps working after it ends |
| **C4** | **Local stdio MCP servers are unownable** | The MCP spec tells stdio servers to read credentials from the environment — so the credential sits in a local, agent-readable config with no audience binding and no broker | Coverage map row #8: **nobody**; MCP authorization spec (2025-06-18 / 2025-11-25) and the boundary analysis that a co-located subprocess shares the runtime's readable environment | The single highest-value unowned vector in the ecosystem is left to `.env` hygiene and hope |

### Why credential brokering is the hardest capability to ship

Policy is a decision (deterministic, local). Telemetry is observation (additive, passive). Credential
brokering is different: it must **hold the crown jewels** while staying usable, be **in the path of every
tool call** without breaking it, span **transports that do not agree** (HTTP request, MCP stdio subprocess
environment, header rewrite, a CLI reading a file), and be **instantly and provably killable**. It is a
distributed system with the most valuable secret in the company inside it — which is also why the
detection-first products underdeliver here: a monitor that learns *after* the theft has already lost. The
only defence the research converges on is architectural — **capability-scoped, session-bound, short-lived
credentials** — which is a broker problem, not a classifier problem (`02-threat-landscape/03`, `05-idea/01`).

## What exists today (and why it is not enough)

| Existing surface | What it does well | Why it is not the answer |
|---|---|---|
| **Secrets managers** (1Password, Doppler, Infisical, Vault, AWS SM) | Central storage, runtime injection, dynamic secrets, masking; increasingly ship a **credential broker** for agents (1Password Credential Broker + Environments; Doppler MCP server; Infisical Agent Vault) | Excellent at *storage and delivery*, but brokering is a bolt-on: no unified **per-tool/per-session** token model across the agent's whole surface, no stdio-MCP virtualization, no ≤1s **session** kill, and no local-first OSS broker with a published attack pack |
| **Enterprise agent identity** (Aembit, Entra Agent ID) | Aembit is the commercial revocation leader — JIT short-lived creds, blended agent+user identity, MCP Identity Gateway (per-tool filtering), one-click kill; Entra adds agent blueprints and Conditional Access | Control-plane-shaped, enterprise-only, quote-priced, HTTP/MCP-gateway-centric; not a five-minute local install, and not stdio-native |
| **AI gateways / MCP portals** (Cloudflare, Solo `agentgateway` STS, Oleria, AWS AgentCore Identity) | RFC 8693 token exchange, audience-bound per-call tokens, downstream credential injection, on-behalf-of semantics | They broker **network** egress; they cannot see or fix the local cases — a stdio server's environment, a CLI reading a credential file |
| **OSS credential isolation** (iron-proxy, secretless-ai, membrane, kloak, Leash header-rewrite) | Prove the pattern: never-in-context creds, default-deny egress, eBPF secret blocking, header rewriting | Single-maintainer / single-harness / single-platform (Claude-Code-only, K8s-only, Linux-only, research-grade); no product, no stdio virtualization, no published kill-time evidence |
| **Platform-native controls** (Claude Code hooks, sandbox-runtime, managed settings) | Zero-setup, inline, per-harness | Single-harness by construction; no cross-harness credential model; the platform structurally will not broker credentials *below* every harness |
| **MCP authorization spec** | Standardizes HTTP-transport authorization | Explicitly defers stdio to "get credentials from the environment" — the gap, stated by the spec itself |

The gap is not "a better vault". The gap is the **broker lifecycle**: reference → resolve → downscope →
inject at egress → use → expire → **revoke** → audit, across mutually incompatible egress points, with the
secret never rendered into the agent's world.

## Why now

1. **The standards converged.** RFC 8693 (token exchange), RFC 8707 (audience binding), RFC 9700
   (security BCP), and RFC 9728 (resource metadata) are published; the IETF **WIMSE "AI Agent
   Authentication and Authorization" (AIMS)** draft — co-authored across OpenAI, Okta, AWS, Ping,
   Zscaler — names the exact shape: an agent workload **identity** (SPIFFE/WIMSE ID), a **short-lived
   credential**, and **OAuth token exchange** carrying delegated authority. The direction is settled; the
   implementation is missing.
2. **The industry just defined the category — and left the OSS lane empty.** In 2026 Aembit shipped an
   MCP Identity Gateway and personal-agent support (Oct 2026); 1Password shipped a Credential Broker and
   "1Password for Agents"; Doppler ships an agent MCP server; Infisical shipped Agent Vault; Solo's
   `agentgateway` shipped an RFC 8693 STS. Every one is a paid or enterprise product. Nobody shipped the
   free, local-first, stdio-inclusive broker — and none publishes a reproducible kill-time benchmark.
3. **The MCP spec localized the gap.** The authorization chapter says stdio servers read credentials from
   the environment; the security best practices forbid token passthrough. The *pattern* is now
   nameable — which is what makes a **spec contribution** possible (own the default implementation).
4. **The producer/consumer ecosystem exists.** agentpolicy emits the `ask`/decision used for step-up
   issuance; agentwatch owns the security-event schema our lifecycle events extend; agenthalt triggers
   revocation; agentdrill measures kill times; agentkernel/agentseatbelt block raw-secret reads as
   defence in depth. agentkeys is the piece that makes each of them real.
5. **The incident record is fresh and the cost is concrete.** In-the-wild credential exfiltration via
   agent injection, coding-agent supply-chain RCE, and 28.65M hardcoded secrets a year make "keep the
   secret out of the agent" a board-level sentence, not a hygiene note.

## What agentkeys is (and is not)

> **"Agents hold references, not secrets — and revoke is a command, not a quarter."**

It is the **broker**, not the vault (backends store); the **layer below every harness**, not a
single-harness hook; the **revocation primitive**, not the policy engine (agentpolicy decides, the
enforcer enforces). It is local-first — a broker process, a CLI, and a local ledger, no cloud dependency —
so a solo developer and an air-gapped enterprise get the same semantics.

## What success looks like

- A **context-dump attack pack** — a simulated full compromise of the agent's context — finds **zero
  usable credentials**. This is a permanent invariant, asserted in CI, not a demo.
- `agentkeys revoke` returns the service to *unauthenticated* in **≤1s**, replay-verified continuously
  (not just at launch) — the single number the product is judged on.
- A **stdio MCP server** authenticates a real tool call while the credential never appears in its config,
  its environment, or the agent's transcript.
- A developer goes from install to a **brokered authenticated tool call in under 15 minutes**, with no
  changes to the agent's code.
- An auditor can reconstruct a **credential lifecycle** for any session — every issuance, use, upgrade,
  and revocation, with principal, binding, and timestamp — and verify the ledger's hash chain.
- Teams migrate credentials **out of `.env` into backends** because the broker makes it easier than the
  status quo (the backend-migration funnel).

See [PRD 04](04-users-and-cujs.md), [PRD 07](07-success-metrics.md) (next), and the scenario catalog.

## Non-goals

No credential creation or rotation (the IdP is the source of truth — we broker, never mint long-lived
secrets); no browser/session credential capture; no enterprise directory sync in v0.1.0; no injection
classifier; no SIEM/console; no multi-tenant SaaS in v0.1.0. Full list in [PRD 14](14-non-goals.md).
