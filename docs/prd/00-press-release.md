# PRD 00 — Press Release / FAQ

**BLUF:** agentkeys is the **never-in-context credential broker for agents** — the layer *below* every
harness that holds the keys. Agents hold only **references**; real secrets stay in OS keychain /
credential-file / secret-manager backends; short-lived, **audience-bound, tool-scoped, session-bound**
tokens are injected **at egress** and never rendered into agent context, arguments, or logs. One command,
`agentkeys revoke`, kills every issued token and brokered session in **≤1s** — verified by replay in CI.
It is the only OSS answer to the two weakest rows in the landscape (**#7 unified revocation**, **#8 stdio
MCP credential handling**) and the only one that is local-first, below-the-harness, and free.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## Press release

### agentkeys — revoke the agent, not the quarter

*Open-sourced today, agentkeys keeps real credentials out of every AI agent's context, injects
short-lived per-tool tokens at the moment of use, and kills all of an agent's access in one second.*

AI agents now hold shell access, filesystem access, and the credentials for the systems that matter —
prod databases, cloud APIs, payment rails, customer data. The most dangerous string in an agent's
context is not the prompt. It is the **API key sitting in its environment**: a static, long-lived,
over-scoped secret with no audience binding and no kill switch, one prompt-injection away from
exfiltration. This is not hypothetical. Anthropic's September 2026 threat-intel report documented
prompt injection *in the wild* exfiltrating production API keys; MCP tool poisoning, rug-pulls, and
cross-server shadowing are demonstrated and unmitigated at the client layer; a single committed `.env`
went on to be scraped within days. And when an agent *does* leak its key, the fix today is a
quarter-long rotation across every system the credential touches.

agentkeys makes the credential the one thing the agent can never steal. Real secrets live in the
backends you already trust — the macOS/Linux keychain, a credential file, and (next) 1Password, Vault,
and K8s Secrets. The agent receives an opaque **reference**. When a tool call actually needs to
authenticate, agentkeys resolves the secret in the broker, mints a **short-lived, audience-bound,
tool-scoped, session-bound** token, and injects it **at egress** — into the HTTP request, the header, or
the child process's environment. The agent's transcript, arguments, and logs never contain anything
usable. And if things go wrong, `agentkeys revoke <agent|session|all>` makes the credential dead in
**under a second** — no rotation, no waiting for a grant to expire, no hunting tokens across systems.

> *"The agent leaked its key" should cost one command, not a quarter of key rotation.*

**How it works**

1. The agent holds a **reference** (`akref:github/pat`, `op://vault/item`, a local handle) — never the
   secret. The reference is safe to log, print, and serialise into the transcript.
2. At the moment of use, agentkeys resolves the reference from the configured backend, mints a
   **downscoped token** (RFC 8693 exchange shape) bound to one **server** (RFC 8707 audience), one
   **tool**, and one **session**, and injects it at egress — never into agent context.
3. For local **stdio MCP servers**, agentkeys virtualizes the environment: the server starts with
   references or a broker-mediated placeholder, and real credentials are supplied by the broker at
   call time. This closes the one row in the coverage map that **nobody** covers.
4. **Expiry is revocation**, and **revocation is explicit**: short TTLs make a leaked token worthless in
   seconds; one command kills everything immediately and refuses the next exchange.
5. Every issuance, use, upgrade, and revocation is an **agentwatch-schema event** in an append-only,
   hash-chained local ledger — a credential lifecycle an auditor can reconstruct per session, joined to
   the session trace by `session_id`.

**Availability:** `pip install agentsec-agentkeys`; Apache-2.0 on GitHub. v0.1.0 is **local-first and
harness-agnostic by construction** — it operates *below* the harness (environment and header
interception generalize across Claude Code, Cursor, Codex CLI, Gemini CLI, and generic MCP clients),
with named recipes for at least two Tier-1 harnesses. It needs **no cloud control plane, no SaaS tenant,
and no third-party account**; it works air-gapped.

## FAQ

**Is this a secrets manager?**
No. A secrets manager *stores* secrets; agentkeys *brokers* them. Your secrets stay in the backend
(keychain, file, and later 1Password/Vault/K8s Secrets) — agentkeys resolves, downscopes, injects, and
revokes. Point it at the vault you already have; you do not migrate your secrets into us.

**Do agents ever see a real secret?**
No — and that is a permanent invariant, not a default. Agent context, tool arguments, and logs carry only
references. Every attempt to read a raw credential outside the broker (`.env` files, cloud credential
files, keychain reads) is a **high-severity event** and, in enforce mode, a block. The invariant is tested:
the context-dump attack pack simulates a full compromise of the agent's context and must find **zero
usable credentials**.

**Revocation in one second — how, if tokens are already short-lived?**
Short TTLs are defence in depth; they are not the mechanism. `agentkeys revoke` invalidates the broker's
session state so the **next exchange refuses**, and the issued tokens are bound to that session, so they
stop authenticating immediately. The kill is measured end-to-end (issue → revoke → replay fails) and
verified **continuously in CI**, not just at launch.

**Does it really handle local stdio MCP servers?**
Yes — this is the flagship gap. The MCP specification tells stdio servers to read credentials from the
environment, which is exactly why a credential ends up in an agent-readable config. agentkeys virtualizes
that boundary: the server is launched under the broker with references/placeholders instead of real
values, and the broker substitutes real credentials at egress. The honest limit is documented: a process
that shares the *same readable runtime* as arbitrary agent code is a hard case, and we say so
([PRD 03](03-landscape.md), [PRD 06](06-security-baseline.md)).

**Is it another Aembit / Entra Agent ID?**
Those are excellent — and enterprise. They are a control plane and an IdP, sold top-down, priced by
quote, and shaped for HTTP/MCP gateways. agentkeys is the opposite end: **OSS, local-first, below the
harness, stdio-inclusive, zero-standing-privilege by construction.** The developer installs it in five
minutes; the platform team keeps their IdP as the source of truth (we broker and revoke; we never mint or
rotate long-lived secrets). And if you already run Aembit or Entra, **keep them** — agentkeys is the
local, stdio-inclusive layer they do not ship, and later (R11/R12) a standards-native client of the same
control planes.

**Why not just use 1Password / Doppler / Infisical Agent Vault?**
Use them — **as backends**. Those products store secrets well and increasingly ship a broker-ish proxy of
their own, but they are commercial vaults first: HTTP-proxy-shaped, no **stdio MCP virtualization**, no
unified per-tool/per-session token model across your *whole* agent surface, no **≤1s session kill** with a
published number, no local-first OSS core, and no reproducible zero-secret evidence. agentkeys is the
broker layer that makes **your** vault never-in-context — including for free, offline, stdio — and
v0.1.x/R10 adds their native adapters so the vault you already pay for becomes one of our backends
([PRD 03](03-landscape.md), [PRD 10](10-feature-parity.md)).

**Does it need a cloud account or a running server?**
No. v0.1.0 is a local broker process + CLI + local store. No tenant, no network trust boundary, works
air-gapped. Server/HA mode is roadmap, not a prerequisite.

**Which harnesses does it work with?**
Because it sits below the harness, environment and header interception works widely; named recipes ship
for **≥2 Tier-1 harnesses at v0.1.0** (Claude Code first), **all 5 by v0.3.0**, plus generic MCP clients
and custom SDKs. There is no single-harness build ([PRD 19](19-harness-compatibility.md), REQUIRED).

**Does it mint long-lived secrets or rotate them?**
Never. agentkeys **brokers**; the org's IdP and secret manager remain the source of truth. We refuse an
anti-feature here: no long-lived issuance, no browser/session credential capture, no password vaulting
([PRD 14](14-non-goals.md)).

**What about step-up for prod credentials?**
Supported: a token upgrade can require a policy/unattended decision first — the production-deploy token
requires a human `ask` (via agentpolicy), and the upgrade is recorded. If nothing approves, no upgrade,
no credential.

**How is this not just an HTTP proxy?**
A proxy only sees network traffic. agentkeys also handles the **local** cases a proxy cannot: the child
process environment for stdio MCP servers, the header rewrite for a gateway, and the plain "a CLI in the
agent's shell wanted a file it shouldn't read." It is a broker with multiple egress-injection points, not
one interception shape.

**What if a backend is down or locked?**
Fail **closed**. An unavailable, ambiguous, or misconfigured backend denies issuance — it never falls back
to a static secret, an env value, or a long-lived token. `agentkeys doctor` explains the effective
backend and the failure semantics.

**How do I know it actually works?**
Two shipped proofs, both in CI: the **context-dump attack pack** (zero usable secrets — a permanent
invariant) and the **revocation replay test** (kill time ≤1s). Plus a public, reproducible benchmark so a
third party can re-run it ([PRD 21](21-evidence-register-and-method.md)). A security product that will not
let you measure it is asking for faith; we do not.

**What is stored?**
References, bindings (audience/tool/session), timestamps, and lifecycle events — never secret material.
Redaction runs before storage, rendering, and audit; every redaction emits a receipt.

**What does it not do?**
It does not decide policy (agentpolicy does), does not enforce in the harness (the enforcer does), does not
store your secrets (your backend does), does not rotate them (your IdP does), and does not run a
multi-tenant SaaS in v0.1.0 ([PRD 14](14-non-goals.md)).
