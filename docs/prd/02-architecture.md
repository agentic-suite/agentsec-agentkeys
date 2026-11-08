# PRD 02 — Architecture

**BLUF:** agentkeys is a **separate broker process** that sits *below* the harness and holds every
credential an agent can reach. The agent carries only a **reference**; at the moment of use the broker
resolves it from a backend, mints a **short-lived, audience-bound, tool-scoped, session-bound** token,
injects it **at egress** (child-process environment, HTTP header, or RFC 8693 exchange), and records the
whole transition in a **hash-chained local ledger** joined to a session trace. The broker is the thing the
agent must not be able to read, edit, or kill ([PRD 06](06-security-baseline.md)); enforcement lives in the
broker, not in the agent's control plane. This document describes the components, the lifecycle, the trust
boundaries, the three injection points, the stdio virtualization boundary, the failure semantics, and the
deployment shapes. The local single-user shape is v0.1.0; server/HA is **R11 (not yet)**.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Components

The broker is **one process** with a small set of internal parts, plus a thin CLI and an SDK
([PRD 05](05-features.md) §B, F20). Everything the broker owns is in-process; everything outside it is a
boundary.

| Component | What it is | Requirement | Built? |
|---|---|---|---|
| **Broker process** | The long-lived daemon. Owns the control channel, the core state machine, the injection engine, and the ledger. Must live **outside the agent's control plane** (cannot be read, edited, or silently killed by the agent). | E10 | Specified |
| **CLI** (`agentkeys`) | Operator surface: `ref`, `run` (stdio wrapper), `revoke`, `export`, `verify-log`, `doctor`, `conformance`. Talks to the broker over a local OS-authenticated channel only. | F20 | Specified |
| **Broker store** | Durable state: sessions, bindings, issuances, revocations, and the hash-chained ledger. Reference driver is **SQLite (WAL)** with declared capability flags. | E2, F15 | Specified |
| **Backend adapters** | Pluggable `resolve(reference) → secret` providers behind one conformance-gated contract. Launch drivers: **OS keychain** and **credential file**. | R5, E9, F7 | Specified |
| **Egress-injection engine** | One interface, three drivers: **env-virtualization**, **HTTP header**, **RFC 8693 token exchange**. Each resolves a reference, applies the binding, injects, and forgets. | R2, E7, E14 | Specified |
| **stdio launch wrapper / sidecar** | Launches a stdio MCP server (or CLI) under the broker under a protected process boundary and supplies credentials at egress, never in the child's config or env. | R8, F12 | Specified |
| **agentwatch sink** | Emitter that ships lifecycle events in the agentwatch schema; the local ledger is authoritative when the sink is unavailable. | R6, E12, F9 | Specified |
| **`doctor`** | Read-only diagnostic: effective backends, capability flags, health, binding/class config, store and clock state. Explains *why* an issuance is denied; never mints. | E4, F8 | Specified |

> **No component in the agent's process.** There is no library the agent imports to "get a secret" and no
> in-process cache the agent can inspect. The broker is reached only over a local, OS-authenticated channel,
> and the secret crosses a process boundary only at egress. This is what "below the harness" means concretely
> (E8, [PRD 19](19-harness-compatibility.md)).

## 2. The credential lifecycle

Every credential use is this ordered transition. Each step that touches a secret is transient, and each
state change appends a ledger entry and emits an event ([PRD 15](15-data-model.md) §4–§5).

| # | Step | What happens | Guard |
|---|---|---|---|
| 1 | **Reference created** | A reference (`akref/1.0`) is registered: backend, path, class, scope-hint. No secret bytes. | R1, E1 |
| 2 | **Agent uses reference** | The agent places the reference in a tool call, config, or env placeholder. The agent never holds the secret. | R1 |
| 3 | **Resolution request** | At the moment of use, the injector/wrapper asks the core to resolve the reference for a specific `(audience, tool, session)`. Idempotent keyed by reference+binding. | E1 |
| 4 | **Backend resolve** | The matching backend adapter resolves reference → secret. Locked, absent, or ambiguous **denies**. The secret lives only inside the broker, transiently. | R5, E4, E9 |
| 5 | **Mint bound token** | The core mints a token bound to `(reference, audience, tool, session)` with a per-class TTL. A higher class triggers a **step-up** request; no approval → no mint. The token uses a 128-bit single-use secret stored **hashed**. | R3, R9, E3 |
| 6 | **Inject at egress** | A driver injects: env-virtualization into the child's environment, HTTP header onto the outbound request, or an RFC 8693 exchange to the downstream STS. Audience is enforced here, by the broker. | R2, E7, E14 |
| 7 | **Use** | The downstream authenticates with the bound, scoped token. `use` is recorded. The broker never forwards a client token upstream. | R6, E14 |
| 8 | **Expire / revoke** | TTL expiry, or `agentkeys revoke <agent\|session\|all>`, flips session state at the store; the **next exchange refuses** and issued tokens stop authenticating **≤1s**. Revocation is never TTL-waiting, never policy-gated. | R4 |
| 9 | **Event + ledger entry** | Each transition appends an append-only, hash-chained ledger row and emits the matching agentwatch event. | R6, E12 |

**Two properties this lifecycle guarantees, by construction:**

- **Idempotent resolution** — a retried resolution keyed to the same reference+binding returns the *same*
  issuance and re-injects nothing new (E1).
- **Fail-closed steps** — at no point does a failure (step 4, 5, or 6) degrade into a static secret, an env
  fallback, or a long-lived token (E4). See §6.

## 3. Trust boundaries

The broker is a mediation point between five distinct trust domains. Each row below is an explicit boundary
with its own control, not an implicit trust.

```
            ┌──────────────────────────────────────────────┐
            │        AGENT'S WORLD  (untrusted)            │
            │  harness ─▶ agent ─▶ tool call w/ reference  │
            └───────────────────────┬──────────────────────┘
                                    │  reference only  (akref/1.0)
             B1  (local OS-authenticated control channel)
                                    ▼
   ┌────────────────────────────────────────────────────────────────┐
   │                   agentkeys BROKER  (separate process)         │
   │   CLI ──control──▶  core state machine ──▶ injection engine    │
   │                                                     ├ env     │
   │                                                     ├ header  │
   │                                                     └ RFC8693 │
   │      ┌───────────────┐            ┌──────────────────────────┐ │
   │      │ backends      │            │ broker store (SQLite)    │ │
   │      │ (adapters)    │            │ sessions·bindings·       │ │
   │      │               │            │ issuances·revocations·   │ │
   │      │               │            │ hash-chained ledger      │ │
   │      └──────┬────────┘            └────────────┬─────────────┘ │
   └─────────────┼──────────────┬───────────────────┼───────────────┘
       B2        │  B3          │  B4               │  B5
                 ▼              ▼                   ▼
          ┌────────────┐  ┌─────────────┐   ┌───────────────────┐
          │  backends  │  │ egress      │   │ ecosystem sinks   │
          │  (secrets) │  │ target /    │   │ agentwatch ·      │
          │ keychain / │  │ downstream  │   │ agentpolicy ·     │
          │ file / SM  │  │ server/STS  │   │ agenthalt         │
          └────────────┘  └─────────────┘   └───────────────────┘
                              B3
```

| Boundary | Parties | Control (who may speak, for what) | Failure posture |
|---|---|---|---|
| **B1 — agent ↔ broker** | Agent/harness ⇄ broker | Local OS-authenticated channel (unix socket, file perms); per-principal broker auth; issuance bound to agent/session identity. The agent may **request** resolution of a reference it is scoped to; it may **not** read the store, edit config, or kill the broker silently. | Unknown principal → deny. No anonymous resolution. |
| **B2 — broker ↔ backends** | Broker ⇄ keychain/file/SM | Backend adapters are conformance-gated and capability-flagged; the broker trusts a backend to *resolve*, never to *widen* a scope. Secrets are unlocked per-exchange. | Unavailable/locked/ambiguous → **deny issuance** (E4, E9). |
| **B3 — broker ↔ egress target** | Broker ⇄ downstream server, API, or STS | Only broker-minted, audience-bound tokens cross. Audience is enforced **at egress**, even if the downstream fails to. No client token passthrough. | Wrong/absent audience → refuse to inject; log `exchange-rejected` (E14). |
| **B4 — broker ↔ ledger** | Broker core ⇄ store | The **only** path from the core to state; append-only, hash-chained, single-writer. Revocation uses CAS on session epoch. | Store down/corrupt → no new issuance; `doctor` non-zero (E2, E4). |
| **B5 — broker ↔ ecosystem** | Broker ⇄ agentwatch / agentpolicy / agenthalt | The broker **asks** agentpolicy for decisions, **emits** to agentwatch, and **accepts** a revoke trigger from agenthalt. It does not decide policy, own the event schema, or gate revocation on policy. | Sink down → local ledger authoritative + gap marker; a policy backend down → step-up **denied** (fail closed). |

> The **identities** in play at these boundaries — the reference, the agent/session, the human subject,
> the workload actor, and the execution credential — are defined precisely in
> [PRD 18 §2](18-issuance-integrity.md) (the identity chain).

## 4. The three egress-injection points

All three drivers sit behind **one** interface (E7). Each exists because a different class of target reads a
credential in a different place, and **no single network gateway reaches all three**. Chosen per target:

| Driver | Target class | Where the secret is applied | Why a network gateway cannot do this |
|---|---|---|---|
| **env-virtualization** | stdio MCP servers, local CLIs, build tools | The broker launches the child under a wrapper; the child's environment is virtualized so the reference resolves to a scoped value **after** the process boundary, at the child's egress. | A gateway sits on the network; it is **not in the child process**. It cannot stop a stdio server reading `GITHUB_TOKEN` from its own env, cannot stop a CLI reading a credential file, and cannot see a stdio JSON-RPC frame that never leaves the host. |
| **HTTP header** | HTTP/JSON APIs, MCP over HTTP, tools that speak REST | The broker attaches `Authorization: Bearer <bound-token>` to the outbound request, overwriting any client-supplied credential. Audience is fixed by the binding. | A gateway *can* attach headers on network egress, but only if it is in the path and only for HTTP. The broker owns the **local** case (a tool calling an API directly, no proxy) and enforces the audience even with no gateway present. |
| **RFC 8693 exchange** | token-based downstreams, STS-fronted services, on-behalf-of flows | The broker performs an OAuth token exchange to obtain a **narrowly audience-bound** token with actor (`act`) semantics for the downstream. | A gateway exchanges tokens at the network edge; the broker exchanges for **this** reference/tool/session binding, using the backend secret as the subject token, and never passes the client's token through (E14). |

**Shared injector rules (no driver may violate them):**

- A driver **cannot widen** an audience or scope beyond the binding; the binding is the ceiling (E7).
- A driver **never** forwards the client's token upstream; it injects a broker-minted, broker-scoped
  credential (E14, MCP security best practices).
- A driver **forgets**: nothing about the resolution is observable to the agent.
- The audience is enforced **at the injector**, not merely requested of the downstream.

## 5. stdio virtualization architecture

The flagship case (R8, F12, coverage row #8) is the local **stdio MCP server** — the process the MCP
authorization chapter explicitly tells to read credentials from its environment, and the vector behind
documented incidents.

```
  harness ──spawn──▶  agentkeys run --server "mcp-server-github" [placeholder cfg]
                              │
                              │  (broker launches the server, not the harness)
                              ▼
                   ┌───────────────────────────────┐
                   │ stdio launch wrapper / sidecar │  protected process boundary
                   │  • child env holds references  │  (own user / sidecar /
                   │  • stdio JSON-RPC is proxied   │   container)
                   │  • broker injects scoped token │
                   │    at the child's egress       │
                   └───────────────┬───────────────┘
                                   │ scoped token (never in child cfg/env/logs)
                                   ▼
                          upstream API / remote MCP
```

- The **agent and the server config** carry only references/placeholders. The server is launched **under the
  broker**, not directly under the harness.
- The child's environment is **virtualized**: the reference resolves to a scoped token at the child's egress,
  so the server's config, env, logs, and the agent transcript contain **no real secret**.
- The reference pattern is documented for server authors and prepared as an **MCP ext-auth contribution**
  ([PRD 20](20-standards-and-claims.md)).

### The honest co-located-runtime limit

A stdio server is a **child process**. If it shares the *same readable runtime* as arbitrary agent code
(co-located subprocess, same user, same environment domain), it can be made to read anything that runtime
can read — the broker cannot fully protect that case. agentkeys addresses this by **moving the credential
across a process boundary** (own user / sidecar / container) and supplies it at egress, not in the child's
env. Where that boundary **cannot** be established, the broker **says so** and records the attempt; it never
claims a guarantee it cannot hold. This is a first-class, documented property — see
[PRD 06](06-security-baseline.md) §4 (the stdio boundary).

## 6. Failure semantics

Fail closed means: **every failure path resolves to *deny* or *pending* — never *allow*, and never silent.**
The matrix below is normative; it is exercised as a fault-injection matrix in CI (E4).

| Failure | Effect on issuance/use | Never happens |
|---|---|---|
| **Backend down** | Deny issuance; surface a structured denial; `doctor` names the backend. Existing issued tokens still expire on their TTL. | No static fallback, no env value, no long-lived token. |
| **Backend locked / absent** | Deny issuance (pending if an unlock is in progress). | No cached plaintext used instead. |
| **Backend ambiguous / partial config** | Refuse to start or deny issuance, naming the failing field. | No "guess which backend", no first-match-wins. |
| **Store down / read-only** | No **new** issuance; `doctor` non-zero; existing sessions remain valid only until TTL. | No in-memory shadow store that outlives the durable one. |
| **Store corrupt / chain mismatch** | Stop issuing; mark `tamper`; require operator action. | Never silently skip a corrupt row or re-anchor the chain. |
| **agentwatch sink down** | Local hash-chained ledger remains **authoritative**, with a **gap marker** for the sink. | Issuance is not silently dropped, and telemetry loss never becomes a grant. |
| **agentpolicy (step-up) down / timeout** | Step-up is **denied** (timeout = deny). | No auto-approve, no "assume allow". |
| **Config ambiguous / integrity check fails** | Refuse to start; loud `tamper` event. | No warn-and-continue. |
| **Clock skew (backwards)** | TTL cannot be extended; expiry fires once. | No resurrection of an expired issuance. |
| **Clock skew (forwards)** | Issuance deemed expired early (deny). | No forward jump that *extends* validity. |
| **Broker process down** | Injection does not occur; the tool call fails. | No credential cached in the agent's reach. |

> The single rule behind the table: **there is no path from any failure to a credential.** A failure is a
> denial with a reason, never a fallback.

## 7. Composition with the ecosystem

agentkeys **brokers and revokes**; it does not decide policy, own the event schema, or enforce in the
harness. Each sibling keeps its lane (separation of duties, [PRD 06](06-security-baseline.md) §3).

| Sibling | Owns | agentkeys' side of the seam |
|---|---|---|
| **agentpolicy** | Whether an issuance/upgrade is **approved** (step-up `ask`, Cedar/AuthZEN decisions) | agentkeys **asks** before minting a higher-class token; **deny** on no-approval/timeout. Revocation is **not** gated on policy. |
| **agentwatch** | The **event schema** and OTel/GenAI ingestion | agentkeys **emits** lifecycle events in the agentwatch schema and keeps the local ledger authoritative ([PRD 15](15-data-model.md) §4). |
| **agenthalt** | The **kill-switch** trigger | agenthalt's trigger causes agentkeys to **revoke** (agent/session/all). Revocation is unconditional and immediate (R4). |
| **agentdrill** | Attack packs and measurement | agentdrill's packs **measure** kill time and the zero-secret invariant against agentkeys (F19). |
| **agentkernel / agentseatbelt** | Local / eBPF **enforcement** | Where composed, they **block** an evasion attempt agentkeys detected; where not composed, agentkeys **records the attempt and names the gap** (R7). |
| **agentgate** | MCP OAuth proxy (Wave 1, HTTP egress) | Complements the broker's **HTTP header** driver; agentkeys covers the **stdio** case agentgate cannot reach. |
| **agentcomply** | Evidence and framework mapping | Consumes agentkeys' export/verify-log output as secret-free evidence ([PRD 15](15-data-model.md) §8). |

## 8. Deployment shapes

| Shape | Description | Status |
|---|---|---|
| **Local single-user** | One broker per developer/machine; local OS-authenticated control channel; SQLite (WAL) store; keychain/file backends; harnesses connect over the local channel. The full v0.1.0 lifecycle in §§2–6 runs here. | **v0.1.0** |
| **Server / HA / fleet** | A central broker for many agents, parent→child delegation with monotonic narrowing, cluster-safe store capability. | **R11 — not yet (P1, v0.1.x–v0.2.0)** |
| **Air-gapped** | Local backends only, no cloud account, no network sink required; ledger remains local and authoritative. | Documented (CUJ-11); full verification **not yet** |
| **Embedded (in a product)** | A host product embeds the broker via the stable SDK/CLI contract (F20). | SDK contract specified; not yet shipped |

> v0.1.0 is deliberately **one process per user**. Multi-node / HA is the R11 forward slate, not a v0.1.0
> claim. Every local guarantee (never-in-context, fail-closed, revoke ≤1s) is stated for this shape only
> until R11 ships.

## 9. Cross-links

- Contracts and event payloads: [PRD 15 — Data Model](15-data-model.md).
- Invariants, STRIDE, stdio boundary, non-claims: [PRD 06 — Security Baseline](06-security-baseline.md).
- Requirements, acceptance criteria, feature catalog: [PRD 05 — Features](05-features.md).
- Personas and journeys exercised against this architecture: [PRD 04 — Users & CUJs](04-users-and-cujs.md).
- Standards this architecture implements/aligns to: [PRD 20 — Standards & Claims](20-standards-and-claims.md).
- Below-the-harness model and Tier matrices: [PRD 19 — Harness Compatibility](19-harness-compatibility.md).
