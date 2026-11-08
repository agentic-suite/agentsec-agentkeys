# PRD 19 — Harness Compatibility

**BLUF:** agentkeys operates **below the harness**. It does not ask Claude Code, Cursor, Copilot, Codex, or
Gemini CLI for permission, hooks, or a plugin API; it virtualizes the **child-process environment** and
injects **HTTP headers / OAuth token exchanges** — two OS/network primitives every harness uses and none can
close. That is why **there is no per-harness fork**: one broker, one set of recipes. The non-negotiable
requirement is **no single-harness build**: **≥2 Tier-1 harnesses at v0.1.0 (Claude Code first)**, **all 5
by v0.3.0** — or documented **lower-layer coverage** where a harness closes its hook surface (e.g. Copilot).
Compatibility is **verified, not asserted**: a harness is "compatible" only when its **agentdrill** attack
pack passes in CI, and every release carries a harness × version table. This document is honest about the
gaps: closed surfaces, GUI-only clients, and Windows.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. The non-negotiable requirement

> **agentkeys MUST NOT be a single-harness build.** It ships as one broker that works across harnesses by
> operating *below* them. At **v0.1.0** it ships named recipes for **≥2 Tier-1 harnesses (Claude Code
> first)**; by **v0.3.0** it covers **all 5 Tier-1 harnesses** — via a first-class recipe *or* documented
> **lower-layer coverage** where the harness's hook surface is closed. A tool is called **compatible** only
> when its **agentdrill** attack pack passes in CI for the tested harness + version.

This mirrors engineering requirement **E8** ([PRD 05](05-features.md)): harness adapters exist *by
construction*, not by porting. Violating it — shipping a build that only works with one harness — is a
release blocker, because it would forfeit the whole point: a cross-harness credential model for a developer
who runs two or three agents on one machine (persona **Sam**, **P4**).

## 2. The below-the-harness model (why there is no fork)

```
        ┌──────────── harnesses (above) ────────────┐
   Claude Code   Cursor   Copilot   Codex CLI   Gemini CLI
        └───────────────────┬───────────────────────┘
                            │  tool calls / child processes / HTTP
        ┌───────────────────▼───────────────────────┐
        │            agentkeys (below)              │
        │  env virtualization · header injection ·  │
        │  RFC 8693 exchange · revoke · ledger      │
        └───────────────────┬───────────────────────┘
                            │  brokered, scoped token
                     backends (keychain / file / later cloud SM)
```

- **The injection points are universal.** A stdio MCP server is a **child process** with an **environment**;
  an HTTP call is a **request with a header**; a token-based downstream accepts an **RFC 8693 exchange**.
  None of these is harness-specific — they are the substrate every harness runs on.
- **The harness stays unmodified.** We never require a hook, a plugin, a fork, or a managed setting. If a
  harness supports MCP or spawns a process or makes an HTTP call, agentkeys can broker it.
- **The only harness-specific artifact is a *recipe*.** A recipe documents *how* to launch that harness's MCP
  server or route its egress through the broker (e.g. point `.mcp.json` at the broker wrapper). It is
  configuration, not code — one broker binary serves all of them.
- **Closed hooks degrade, they do not block.** Where a harness closes its hook surface (Copilot), the
  broker still operates at the **lower layer** — the process/network boundary — and the recipe documents
  the reduced coverage honestly. "Covered at a lower layer" ≠ "first-class hook recipe"; the compatibility
  table says which is which.

Consequence: **adding a harness is a recipe + a passing attack pack, not a product fork.** That is what keeps
the model cross-harness as the field churns.

## 3. Tier 1 — coding agents (the priority surface)

Tier 1 is where a developer's real work happens and where the credential leak is worst: the harness holds
the agent loop, spawns MCP servers, and runs shell commands with an environment.

| Harness | Why targeted | agentkeys angle | v0.1.0 | v0.3.0 |
|---|---|---|---|---|
| **Claude Code** *(first)* | The reference agent CLI; MCP-native; documented credential-in-config failure mode; largest installed base | stdio MCP env virtualization via `.mcp.json` → broker wrapper; header injection for HTTP MCP | **✅ recipe #1 (first)** | ✅ |
| **Cursor** | Desktop IDE agent, large audience, MCP client; shares the same env/header substrate | env virtualization for its MCP servers; header injection for API egress | **✅ recipe #2** | ✅ |
| **GitHub Copilot (agent mode)** | Huge reach; **hook surface is closed** | Covered at a **lower layer** — process/network interception, not a first-class hook | **documented lower-layer** | ✅ lower-layer documented |
| **OpenAI Codex CLI** | CLI agent, env + stdio MCP, developer-native | env virtualization + header injection recipe | **not yet** | ✅ |
| **Gemini CLI** | CLI agent, MCP + shell, Node runtime | env virtualization + header injection recipe | **not yet** | ✅ |

**v0.1.0 count:** Claude Code + Cursor = **2 first-class recipes** (requirement met; Claude Code first).
Copilot is **covered at a lower layer** but is *not* claimed as a first-class hook recipe.
**v0.3.0 count:** all 5 — each as a first-class recipe **or** documented lower-layer coverage.

### 3a. What a Tier-1 recipe contains

A recipe is the small, harness-specific *documentation + config* that points a harness at the one shared
broker. It never contains code paths inside the broker. Each recipe ships:

1. **Launch wiring** — how the harness's MCP server (or CLI child process) is launched through the broker
   wrapper so its environment holds **references**, not secrets (R8, E7).
2. **Egress wiring** — how the harness's HTTP calls are routed to the broker's header injector, or how a
   token-based downstream is reached via RFC 8693 exchange (R2, E7).
3. **A reference example** — the exact `akref:`/placeholder form the user pastes, and the `.env`→reference
   migration note (F1).
4. **The agentdrill pack name** — the per-harness attack pack that gates the recipe in CI (§6).
5. **Tested harness version** — pinned, because recipes rot when harnesses change (§7).

Because all five recipes share steps 1–3 through the same contract, the marginal cost of a new harness is a
document, a pack, and a pinned version — **never a fork**.

## 4. Tier 2 — agent frameworks (brokered by construction)

A framework is a library the embedder (**Alex**, **P5**) uses to build an agent; it is *not* a process we
wrap. Because agentkeys brokers at the **env / header / exchange** layer, a framework that launches tools or
makes HTTP calls is **brokered by construction** — **no per-framework adapter is required**. Recipes help
the embedder wire it up; they are not a compatibility gate the way Tier-1 packs are.

| Framework | How it reaches credentials | How agentkeys brokers it | Per-framework adapter | Status |
|---|---|---|---|---|
| **LangChain / LangGraph** | Tools read env / make HTTP calls | env virtualization + header injection | Not needed; recipe | documented |
| **CrewAI** | Tools + env-based secrets | env virtualization + header injection | Not needed; recipe | documented |
| **OpenAI Agents SDK** | Tools, MCP, HTTP egress | env virtualization + header injection | Not needed; recipe | documented |
| **AutoGen / AG2** | Tools, code exec, env | env virtualization + header injection | Not needed; recipe | documented |
| **LlamaIndex** | Tools, MCP, HTTP egress | env virtualization + header injection | Not needed; recipe | documented |
| **PydanticAI** | Tools, HTTP egress | header injection + env virtualization | Not needed; recipe | documented |
| **smolagents** | Tools, code exec, env | env virtualization + header injection | Not needed; recipe | documented |

Honesty: Tier 2 is **not individually CI-verified** at v0.1.0. It is brokered "by construction" because the
substrate is generic; the recipes are **documented**, not **field-tested**, until a pack runs for them.

## 5. Tier 3 — generic MCP clients and enterprise platforms (via standards)

Tier 3 is reached through **standards**, not bespoke integration: MCP Authorization (2025-06-18 /
2025-11-25) for HTTP egress, env virtualization for stdio, and RFC 8693/8707/9728 for token exchange.

| Tier 3 surface | Examples | agentkeys path | Honest status |
|---|---|---|---|
| **Generic MCP clients** | Claude Desktop; any MCP client | stdio env virtualization; HTTP header injection via MCP auth | documented; **Claude Desktop is GUI-only** (see §7) |
| **Enterprise agent platforms** | Copilot Studio, Agentforce, Bedrock agents | HTTP egress header injection + RFC 8693 exchange; audience-bound token | design-aligned; **not individually verified** at v0.1.0 |
| **Custom SDK / embedding** | bespoke agent runtimes | stable CLI + SDK contract (F20, E1); env/header/direct store contract | documented |

The enterprise tier is where the **ecosystem** (agentgate, agentwatch) and the standards do the heavy
lifting; agentkeys supplies the local, below-the-harness broker those standards assume exists.

## 6. Compatibility is verified, not asserted

The word "compatible" is a claim, and claims follow [PRD 20](20-standards-and-claims.md)'s honesty ladder.

- **agentdrill ships per-harness attack packs.** Each pack reproduces the credential-leak scenarios a given
  harness makes possible (context dump, `.env` read, MCP config secret, header capture, replay). **agentdrill**
  is the sibling that owns these; agentkeys consumes the packs as its compatibility gate.
- **A harness is "compatible" only when its pack passes in CI** for the tested harness **version**. No pack,
  no claim.
- **Release notes carry a harness × version compatibility table.** The table is generated from the CI run
  (which packs passed, which versions), never hand-filled with optimism.
- **Honest labels.** Each row is one of: *first-class recipe* (hook/recipe shipped + pack green) ·
  *lower-layer coverage* (hook closed, substrate interception + pack green) · *documented* (reciped, pack not
  yet green) · *not yet*.
- **New harnesses arrive via community adapters.** A third party adds a recipe + a pack under the adapter
  contract ([PRD 05](05-features.md) E8/E9); it is admitted to the compatibility table only when its pack
  passes — the same bar we hold ourselves to.

## 7. Honest gaps (do not over-claim)

| Gap | Reality | Posture |
|---|---|---|
| **Closed hook surfaces (Copilot, others)** | No public hook to wrap; we intercept at the process/network layer instead | **Lower-layer coverage**, labeled as such — never presented as a first-class hook recipe |
| **GUI-only clients (e.g. Claude Desktop)** | No agent-spawnable process env for a UI-driven flow; stdio/HTTP paths depend on what the client exposes | Covered **where the client exposes stdio/HTTP**; otherwise a documented gap |
| **Windows** | Not supported at v0.1.0 | macOS + Linux first; Windows on demand ([PRD 03](03-landscape.md) §4) |
| **Version drift** | Harnesses change quickly; a recipe can rot | Recipes are **pinned to tested versions**; the compatibility table states the tested version |
| **Tier 2 / Tier 3 verification** | Brokered "by construction", not individually pack-gated at v0.1.0 | Labeled **documented / not yet**, not *verified* |
| **Co-located same-runtime stdio** | A process sharing the agent's readable runtime is a hard case | Documented boundary ([PRD 06](06-security-baseline.md) §4); recorded, not guaranteed |

None of these is hidden. The compatibility table is designed to make a missing row **visible**, which is the
only way a cross-harness security claim stays trustworthy as the ecosystem moves.
