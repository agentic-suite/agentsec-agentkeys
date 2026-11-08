# PRD 16 — Adapters & Integration

**BLUF:** One broker, many integrations — and every one of them is **thin by rule**. agentkeys has five
adapter surfaces: **harness recipes** (configuration documents, never code forks), **egress drivers**
(env-virtualization, HTTP header, RFC 8693 exchange — the only places code touches a credential),
**backend adapters** (conformance-gated `resolve()` providers), the **embedder surface** (a stable SDK/CLI
contract that must stay out-of-process), and the **ecosystem seams** (agentpolicy, agentwatch, agenthalt,
agentdrill). This document is the guide an integrator actually uses: per-harness recipes with exact config
shapes, the generic recipes for any stdio MCP client / HTTP API / token-exchange target, the rules that keep
every adapter from becoming a product fork, and how a new adapter is admitted. Adding a harness is a recipe
plus a passing attack pack — **never a code change in the broker**.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. The five adapter surfaces

| Surface | What it is | Code or config? | Gate |
|---|---|---|---|
| **Harness recipes** (§2) | Per-harness wiring docs + config snippets that point a harness at the broker | Config + docs only | The harness's agentdrill pack green in CI ([PRD 19](19-harness-compatibility.md)) |
| **Generic recipes** (§3) | The same wiring for any stdio MCP client, any HTTP API, any exchange target | Config + docs | The generic conformance fixtures |
| **Egress drivers** ([PRD 02 §4](02-architecture.md)) | The three injection points — the only code that touches a credential | **Broker code** | Driver conformance fixtures (E7, E14) |
| **Backend adapters** (§5) | `resolve(reference) → secret` providers (keychain, file; R10 adds vaults) | Broker plugin code | The backend conformance suite (E9) |
| **Embedder surface** (§4) | SDK + CLI for a host product to drive the broker | Client code, **out-of-process only** | Contract fixtures (E1) |
| **Ecosystem seams** (§6) | agentpolicy `ask`, agentwatch sink, agenthalt trigger, agentdrill packs | Adapters, thin by rule | Ecosystem contracts |

**The one rule that keeps this a product and not N forks:** a harness recipe may **change configuration
files the user owns** (`.mcp.json`, `settings.json`, `config.toml`); it may **never** require a broker code
change, a harness fork, or a plugin binary. The moment a harness needs code, the broker's design is wrong.

## 2. Tier-1 harness recipes (v0.1.0: Claude Code + Cursor; v0.3.0: all 5)

Every recipe has the same five parts ([PRD 19 §3a](19-harness-compatibility.md)): **launch wiring**
(the harness's MCP servers start under the broker wrapper), **egress wiring** (where its HTTP calls get
headers/exchange), **the reference form** to paste (and the `agentkeys scan`/`migrate` path that writes it
for you, R17), **the pack name** that gates it, and the **pinned harness version**.

### 2.1 Claude Code (recipe #1 — first)

| | |
|---|---|
| **What it touches** | `.mcp.json` (project) / `~/.claude.json` (user) MCP server entries; optionally `.claude/settings.json` env placeholders |
| **Launch wiring** | Point each local server's `command` at the broker wrapper: `"command": "agentkeys", "args": ["run", "--server", "npx", "-y", "@modelcontextprotocol/server-github"]` — the wrapper spawns the server with a **virtualized env** holding references, and the broker injects scoped tokens at the server's egress (R8). |
| **Reference form** | `"env": { "GITHUB_TOKEN": "akref:keychain/agentkeys/dev/github-pat" }` — `agentkeys migrate` writes this for you from the current literal value (R17). |
| **Egress wiring** | HTTP tools route via the broker header driver (`HTTPS_PROXY`-free: a per-tool env hook or the wrapper's injected session config); hooks are **optional**, never required. |
| **What must NOT change** | The Claude Code binary, its settings schema, or anything outside the user's config files. |
| **Verification** | Recipe ends in a verified authenticated call; the Claude Code agentdrill pack (context-dump, `.env` read, MCP-config secret, replay) green in CI. |
| **Pinned version** | Recipe states the exact Claude Code version tested; drift is a visible gap, not a silent break. |

### 2.2 Cursor (recipe #2)

| | |
|---|---|
| **What it touches** | `.cursor/mcp.json` (project) / `~/.cursor/mcp.json` (user); `permissions.json` untouched |
| **Launch wiring** | Identical wrapper pattern to Claude Code — Cursor's MCP entries take `command`/`args`/`env`, so `"command": "agentkeys", "args": ["run", "--server", …]` and reference-form `env` values. |
| **Egress wiring** | Cursor's HTTP tool calls get the header driver via the wrapper-injected egress config. |
| **Verification** | Same pack shape, Cursor-pinned. |
| **Honest note** | Cursor's network sandbox may interact with the wrapper; the recipe documents the tested combination. |

### 2.3 OpenAI Codex CLI (v0.3.0) and Gemini CLI (v0.3.0)

Both are config-driven MCP clients (`config.toml` `[mcp_servers.*]` and `settings.json` `mcpServers`
respectively) with the same `command`/`env` shape — the **same wrapper and reference pattern** applies, so
the marginal cost is the recipe doc, the pinned version, and the pack. They are scheduled, not built
([PRD 09 §6](09-roadmap.md)).

### 2.4 GitHub Copilot agent mode (lower-layer coverage, honestly)

Copilot's hook surface is closed; agentkeys covers it at the **process/network layer** the same env/header
drivers already use, labeled *lower-layer coverage* — never presented as a first-class recipe
([PRD 19 §7](19-harness-compatibility.md)). If Copilot ships an open hook surface later, the recipe
promotes with no broker change.

## 3. Generic recipes (any client, any target)

| Recipe | Shape | Notes |
|---|---|---|
| **Any stdio MCP client** | `"command": "agentkeys", "args": ["run", "--server", <original command…>]` + reference-form `env` | Works for any client that spawns servers with `command`/`env` (VS Code, Cline, Windsurf, custom hosts). The wrapper proxies stdio JSON-RPC untouched — logs to stderr only. |
| **Any HTTP API tool** | Bind the reference to the target's audience; the tool's request gains an injected `Authorization` header at egress | The agent never sees the header; audience is fixed by the binding (E14). |
| **Token-exchange targets** | Backend secret (or session credential) as RFC 8693 `subject_token` → narrow audience-bound mint with `act` semantics | For STS-fronted downstreams; the broker never passes the client's token through. |
| **Plain CLIs in the agent's shell** | `agentkeys run -- <command>` gives the child a virtualized env for its run | For non-MCP tools that read env credentials; the reference resolves at the child's egress, not in the shell. |

## 4. Embedder surface (Alex, P5)

- **Out-of-process, always.** The SDK is a **control-plane client** (ask the broker to resolve/issue/
  revoke), never a secret library. There is no `get_secret()` anywhere in the SDK — a host product that
  wants the plaintext is our anti-feature ([PRD 14 §4](14-non-goals.md)).
- **Stable contract.** `akref/1.0` + `issuance/1.0` are additive-only (E11); the CLI exit codes and the
  SDK surface are stable within v0.x.
- **Recipes:** LangGraph — a tool node resolves via the broker CLI at execution time and passes the
  *injection handle* to the egress driver, so the graph holds references in state, never values. OpenAI
  Agents SDK — same shape in a function tool. Both are documented examples that run against the conformance
  fixtures, not per-framework adapters (Tier-2 is brokered by construction,
  [PRD 19 §4](19-harness-compatibility.md)).

## 5. Backend adapters (adding a backend)

One `Backend` interface: `resolve(reference) → secret`, `list`, `health` — with semantics every driver MUST
provide: **never-log**, **resolve-at-use**, **fail-closed on ambiguity**, declared **capability flags**
(E9). Adding a backend (ours at R10, or a third party's via entry points) is:

1. Implement the contract (a single module, no broker-core changes).
2. Pass the **conformance suite** — including the fail-closed fault fixtures (locked, absent, ambiguous,
   slow) and the no-log scanner.
3. Be **admitted at load** or not at all: a failing backend never runs "best effort".

v0.1.0 ships **OS keychain** (macOS Keychain / Linux Secret Service) and **credential file**. R10 adds
1Password, Vault, K8s Secrets, AWS/GCP/Azure SM under the identical gate.

## 6. Ecosystem seams (thin by rule)

| Seam | Direction | Contract |
|---|---|---|
| **agentpolicy** | agentkeys → ask (step-up, R9); never decide | `ask`/decision record; timeout = deny; revocation is **never** policy-gated (D-07) |
| **agentwatch** | agentkeys → emit lifecycle events (R6) | additive event set, `event_version` per the schema process |
| **agenthalt** | agenthalt → trigger `revoke` (R4) | revoke scopes: agent/session/all; event recorded with the trigger source |
| **agentdrill** | packs → gate recipes | per-harness attack packs; a recipe without a green pack is *documented*, not *compatible* |
| **agentcomply** | export → evidence | `agentkeys export` JSONL + `verify-log`; secret-free by scan (E5) |

## 7. Adapter governance

- **Recipes are pinned** to tested harness versions; the compatibility table in release notes carries
  harness × version and is **generated from the CI run**, never hand-filled.
- **Drift is visible**: a harness update that breaks a recipe fails its pack — the failure is the
  early-warning system, not a user support ticket.
- **Community adapters** (recipes, backends, packs) are admitted at the same bar we hold ourselves:
  conformance green, pack green, docs honest. No exceptions for friends.
- **The anti-fork rule is a release gate**: any PR that adds harness-specific code to the broker core must
  justify itself against this document or be rejected (E8, D-03).

## 8. Related documents

- Why there is no per-harness fork: [PRD 19 — Harness Compatibility](19-harness-compatibility.md).
- The drivers these recipes wire to: [PRD 02 §4](02-architecture.md).
- The contracts recipes reference: [PRD 15 — Data Model](15-data-model.md).
- What a recipe must never become: [PRD 14 — Non-goals](14-non-goals.md).
