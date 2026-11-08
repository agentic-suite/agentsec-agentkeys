# PRD 03 — Landscape

**BLUF:** Credential handling for agents is no longer an empty space — it is a **crowded, converging
space** with a glaring hole. Aembit and Entra Agent ID own enterprise agent identity; 1Password, Doppler,
Infisical, Vault, and AWS own secret storage and, increasingly, an agent-facing broker; Cloudflare,
Solo `agentgateway`, Oleria, and AWS AgentCore own *network* egress token exchange; and a handful of OSS
projects (iron-proxy, secretless-ai, membrane, kloak, Leash) prove the never-in-context pattern. What
**nobody** ships is the combination that matters for a developer: an **OSS, local-first, below-the-harness
broker** that unifies revocation, virtualizes **stdio MCP** credentials (**coverage row #8 — nobody**),
and proves its kill-time with a public benchmark. That is the lane agentkeys takes, deliberately.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. What already solves part of this

### 1a. Enterprise agent identity / access control

| Product | Model | Strengths | Where it stops short of agentkeys |
|---|---|---|---|
| **Aembit** | Workload Access Management control plane | The clear commercial **revocation** leader: JIT short-lived, scoped credentials; blended agent+user identity; **MCP Identity Gateway** with per-tool filtering; conditional access (posture/geo/time); one-click kill; SIEM export; ISO 27001 | Tenant control plane, enterprise-only, quote-priced; gateway/HTTP-shaped (not stdio-native); not a five-minute local install; no published reproducible kill-time benchmark |
| **Microsoft Entra Agent ID** (+ Defender XDR) | First-party agent identity | Agent blueprints, parent-child identity, centralized revocation, Conditional Access | Microsoft-ecosystem-bound; identity scope only |
| **CyberArk Secretless Broker** | Protocol-aware service connector | The precedent for injecting auth *outside* the application | Human/legacy-workload shape; not agent-lifecycle/OTel-native |
| **Oleria, Solo `agentgateway`, AWS AgentCore Identity, Ping** | RFC 8693 token-exchange gateways / STS | Session credential exchanged **per call** for a narrow audience-bound token with on-behalf-of (`act`) semantics; one-place revocation; SPIFFE JWT-SVID as actor token | Network egress only; they cannot fix a stdio server's environment or a CLI reading a credential file |

### 1b. Secrets managers (storage — increasingly with an agent broker)

| Product | Agent-facing capability | Where it stops short |
|---|---|---|
| **1Password** (Credential Broker, Environments, for Agents, NVIDIA OpenShell beta) | Runtime credential brokering scoped per job, human+agent attribution, MCP server that **never returns secret values**, placeholders inside a sandbox | Commercial; the broker is an add-on to a password manager; no unified per-tool/per-session token model across the agent's whole surface; no stdio virtualization; no OSS attack pack |
| **Doppler** | MCP server so agents request secrets natively; agent-scoped OIDC service accounts; dynamic secrets; mask-from-humans | Commercial; storage/resolution, not a full broker lifecycle with session kill |
| **Infisical Agent Vault** | HTTP credential **proxy**: agent sends a placeholder, proxy attaches the real credential on egress (method/path rules); works with Claude Code / OpenClaw | HTTP-proxy shape; no stdio-MCP virtualization; per-request policy, not session-bound revoke-cascade |
| **HashiCorp Vault / AWS Secrets Manager** | Dynamic secrets, leases, every enterprise backend | Not agent-shaped: no per-tool scope, no session binding, no agent-native revoke, no stdio story; HCP Vault Secrets SaaS retired July 1 2026 |

### 1c. OSS credential isolation (the pattern, unproductized)

| Project | Strength | Gap |
|---|---|---|
| **ironsh/iron-proxy** | Default-deny MITM egress + server-side secret injection (never-in-context) | Niche, low community; network-only |
| **opena2a-org/secretless-ai** | Claude Code PreToolUse hook + keychain/1Password backend | Claude-Code-specific |
| **strongdm/leash** | Wraps agents in containers; per-cgroup Cedar via eBPF; **credential header rewriting** | Linux/containers; per-agent wrapper UX |
| **noperator/membrane, spinningfactory/kloak** | eBPF egress allowlist / K8s secret injection | Experimental / K8s-only |
| **otscup/secrets-broker-skill** | Portable agent skill + stdio MCP bridge with OAuth 2.1 | Skill-and-bridge, not a broker product; remote MCP endpoint required |
| **snyk/agent-scan** | MCP/tool scanning (poisoning, sensitive params) | Detection/scanning, not brokering |

### 1d. Platform-native & spec layers

- **Claude Code hooks / managed settings, Cursor, Codex config, Gemini CLI** — zero-setup, inline,
  single-harness; no cross-harness credential model.
- **MCP authorization chapter** (2025-06-18 / 2025-11-25) — standardizes HTTP-transport auth and
  **explicitly tells stdio servers to read credentials from the environment**: the gap, stated by the spec.
- **SPIFFE/SPIRE**, **RFC 8693/8707/9700/9728**, **IETF WIMSE/AIMS** (OpenAI · Okta · AWS · Ping ·
  Zscaler · Defakto), **ID-JAG**, **transaction tokens**, **DPoP** — the standards now name the shape
  (agent workload identity → short-lived credential → token exchange). Standards are ahead of OSS supply.

## 2. The whitespace (from the ecosystem coverage map)

| # | Capability | Commercial | OSS | Verdict |
|---|---|---|---|---|
| 7 | Credential revocation / JIT creds | `●●○` (Aembit, Entra) | `●○○` (single-maintainer experiments) | **Weak everywhere** |
| 8 | **STDIO MCP credential handling** | `○○○` | `○○○` | **Nobody** |
| — | Dev-native, local-first broker UX | `○○○` (all quote-driven / SaaS) | `●○○` (sysadmin-grade) | **Near-nobody** |
| — | Public, reproducible kill-time / zero-secret **evidence** | `○○○` | `○○○` | **Nobody** |

Three of these are agentkeys' entire reason to exist; the fourth (evidence) is our trust strategy.

## 3. Where agentkeys fits (honest position)

> **agentkeys is the OSS, local-first, below-the-harness credential broker**: the free, five-minute,
> stdio-inclusive answer to the landscape's weakest capability — and the only one that proves its
> kill-time and its zero-secret invariant in a public benchmark.

- **We complement, not replace, the enterprise brokers.** Aembit/Entra/1Password/Doppler own the paid
  control plane; agentkeys owns the free, local, developer-native layer and interoperates with the backends
  and the IdP as the source of truth.
- **We do not fight on their turf:** no compliance letters, no enterprise platform integrations, no SOC
  workflow — those are cost moats (the ecosystem coverage map calls them "their defensible turf"). We take
  the OSS enforcement/plumbing lane and the three unowned rows.
- **Our wedge is structural:** we sit *below* every harness (env + header interception generalizes), which
  is exactly the layer platforms will not build and gateways cannot reach.

## 4. Honest v0.1.0 gaps (do not over-claim)

| Not in v0.1.0 | Reality | When |
|---|---|---|
| Server / HA / multi-tenant mode | Single-user local broker + local store | v0.2.0 |
| 1Password / Vault / K8s backends | v0.1.0 ships **OS keychain + credential-file** only | v0.1.x |
| SAML/SCIM, enterprise directory sync | Not an identity provider — we broker | roadmap |
| Browser/session credential capture | **Refused permanently** (anti-feature) | never |
| Windows support | macOS + Linux first | roadmap (measure demand) |
| Full eBPF secret-blocking | agentkernel's job; we emit the event | ecosystem |
| A GUI | CLI + local ledger | roadmap |

Labeled honestly, per the ecosystem's own convention: *documented* today, *field-tested* only after a
hand-maintained field-test report says so.
