# PRD 05 — What (Features)

**BLUF:** agentkeys v0.1.0 is the **complete never-in-context credential lifecycle**: agents hold only a
**reference**, the broker resolves it from a backend, mints a **short-lived, audience-bound, tool-scoped,
session-bound** token, injects it **at egress** (child-process environment for stdio MCP, HTTP header, OAuth
token exchange), and records every issuance/use/upgrade/revocation in a **hash-chained** local ledger. It
handles the local cases a gateway cannot — **stdio MCP credential virtualization** (the unowned coverage
row #8) — flags **raw-credential reads**, gates prod-class scope behind a **step-up approval**, and makes
`agentkeys revoke` kill all of an agent's access in **≤1s**, replay-verified in CI. Then
`agentkeys scan`/`migrate` moves your existing secrets out of `.env` and MCP configs in minutes — the
adoption unlock — and `agentkeys posture` (v0.1.x) keeps the residual risk visible. Local-first, one CLI,
no cloud account, harness-agnostic by construction.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## v0.1.0 scope (one sentence)

Everything an agent needs to *authenticate to a real system* without ever holding the credential — and
nothing that decides policy, stores your secrets, or mints a long-lived secret.

## Requirement IDs and how to read them

- **R#** — product requirements. **R1–R9 + R17 are the v0.1.0 P0 core**; **R10–R12 + R18 are P1
  (v0.1.x–v0.2.0)**; **R13–R16 are the forward product-depth slate (P2, v0.3.0+)**.
- **E#** — engineering requirements: the security/protocol/ops properties without which the product is
  unsafe to ship. **E1–E15 are all P0 for v0.1.0** (E13–E15 are standards/supply-chain gates).
- Priority: **P0** v0.1.0 · **P1** v0.1.x–v0.2.0 · **P2** v0.3.0+.
- Mapping to the ecosystem PRD (`213-agentkeys.md`): our R1–R7 = its R1–R7; our **R8 = its R10 (stdio,
  promoted to P0 — the flagship)**; our **R9 = its R9 (step-up, promoted to P0)**; our **R10 = its R8
  (enterprise backends)**; our **R12 = its R11 (SPIFFE)**; our **R18 = its R12 (credential health
  reports)**; our R17 and R13–R16 are new here. Line-by-line trace:
  [Appendix A](appendix-a-consolidated-prd.md).

## A. Core requirements (R1–R9 + R17, P0 for v0.1.0)

### R1 — Reference-only context (never-in-context) (P0)

| | |
|---|---|
| **Requirement** | The agent holds only a **reference** (`akref:<backend>/<path>`, `op://…`, a local handle). Real secret material is **never** rendered into agent context, tool arguments, generated code, or logs. |
| **Why it is first** | This is the permanent invariant: a prompt injection that dumps the context must yield nothing usable. |
| **Reference safety** | A reference is designed to be safe to print, serialise, and log: no secret bytes, resolvable only by the broker, scoped by backend policy. |
| **Acceptance** | Simulated full context-dump (transcript + env + args + config + logs) finds **zero usable credentials**, across every scenario variant — CI-gated, not a demo. |
| **Test** | context-dump attack pack; `tests/test_reference_leak.py`. |

### R2 — Moment-of-use egress injection (P0)

| | |
|---|---|
| **Requirement** | Real credentials are resolved at the moment of use and injected **at egress** — never into the agent. The engine is **transport-agnostic**: (a) child-process **environment virtualization** (stdio MCP / CLIs), (b) **HTTP header** injection (gateways, APIs), (c) **OAuth token exchange** (RFC 8693) for token-based downstreams. |
| **Injection rule** | The injector sees a reference and a target; it resolves, downscopes, injects, and forgets. Nothing about the resolution is observable to the agent. |
| **Acceptance** | A real authenticated tool call completes end-to-end for each transport (env, header, exchange); the agent's transcript contains only the reference. |
| **Test** | `tests/test_inject_env.py`, `tests/test_inject_header.py`, `tests/test_inject_exchange.py`. |

### R3 — Token model: short-lived, audience-bound, tool-scoped, session-bound (P0)

| | |
|---|---|
| **Requirement** | Every issued token is (1) **short-lived** (per-class TTL with floor/ceiling), (2) **audience-bound** to one server (RFC 8707 resource indicator), (3) **tool-scoped** to one tool/operation, and (4) **session-bound** to one conversation/session. |
| **Why it matters** | This is the one defense class every expert and skeptic endorses (research, `05-idea/01`): expiry *is* revocation, and binding kills confused-deputy/replay. |
| **Acceptance** | Each binding demonstrated by an attempt to replay/reuse the token elsewhere (wrong server / wrong tool / after session end) — **fails** and is logged `exchange-rejected`. |
| **Test** | `tests/test_binding_audience.py`, `tests/test_binding_tool.py`, `tests/test_binding_session.py`. |

### R4 — One-command revocation in ≤1s (P0)

| | |
|---|---|
| **Requirement** | `agentkeys revoke <agent\|session\|all>` invalidates the broker session so the **next exchange refuses**, and the session-bound issued tokens stop authenticating. Emits a `revoked` event with the operator/target. |
| **Not TTL-waiting** | Revocation is explicit and immediate; short TTLs are defence in depth, not the mechanism. |
| **Acceptance** | Measured end-to-end (issue → revoke → replay fails) **≤1s**, verified **continuously in CI** (not only at launch). Scoped kills (`agent`/`session`) do not over-kill (`all` is explicit). |
| **Test** | `tests/test_revoke_killtime.py`, `tests/test_revoke_scope.py`. |

### R5 — Backends: OS keychain + credential file, pluggable, fail-closed (P0)

| | |
|---|---|
| **Requirement** | Launch backends: **OS keychain** (macOS Keychain, Linux Secret Service) and **credential files on disk** as a fallback. The backend contract is **pluggable** (E9) and **fail-closed**: an unavailable/ambiguous/misconfigured backend **denies issuance**. |
| **Never-fallback rule** | No path degrades to a static secret, an env value, or a long-lived token. |
| **Acceptance** | Documented backend matrix + failure semantics; the fail-closed fault matrix (locked/absent/ambiguous/partial-config) is deny-or-pending on every path. `doctor` explains the effective backend. |
| **Test** | `tests/test_backend_keychain.py`, `tests/test_backend_file.py`, `tests/test_failclosed_matrix.py`. |

### R6 — Credential-lifecycle events + hash-chained ledger (P0)

| | |
|---|---|
| **Requirement** | Every **issuance / use / upgrade / revocation / exchange-rejection / evasion** is (a) an **agentwatch-schema** event and (b) an entry in a local **append-only, hash-chained** ledger. |
| **Join keys** | `session_id`, `agent_id`, `reference_id`, `binding` (audience/tool) — a lifecycle record joins to the session trace by `session_id`. |
| **Reconstruction** | `agentkeys export --session <id>` emits an ordered JSONL timeline with principal, binding, timestamps, reasons, and the hash chain; `verify-log` confirms integrity. |
| **Acceptance** | Full credential lifecycle reconstructable per session; the chain verifies; a corrupted row is **detected, not skipped**; a scan finds no secret material in the export. |
| **Test** | `tests/test_ledger_chain.py`, `tests/test_export.py`. |

### R7 — Secret-evasion detection (P0)

| | |
|---|---|
| **Requirement** | Attempts to read env/file credentials outside the broker (`.env`, cloud credential files, keychain reads) are **high-severity events**; in **enforce** mode they are **blocked** where an enforcer composes (agentkernel/agentseatbelt). |
| **Honesty rule** | agentkeys never claims to have blocked what it could not: if no enforcer covers the path, it records the attempt and names the gap. |
| **Acceptance** | The evasion pack is caught in monitor-safe mode; blocked-and-logged in enforce mode where an enforcer is composed. |
| **Test** | `tests/test_evasion_detect.py`, `tests/test_evasion_enforce.py`. |

### R8 — stdio MCP credential virtualization (P0 — the flagship, unowned row #8)

| | |
|---|---|
| **Requirement** | Local **stdio MCP servers** receive credentials **through the broker**, not from their config or environment: the server is launched under the broker with references/placeholders, and the broker supplies a scoped token at egress. The server's config, env, logs, and the agent transcript contain no real secret. |
| **Why it is the flagship** | The MCP spec tells stdio servers to read credentials from the environment — the exact vector behind multiple documented incidents — and **no product covers it** (coverage map row #8). |
| **Honest limit** | A process that shares the *same readable runtime* as arbitrary agent code cannot be fully protected; the broker requires a protected process boundary (sidecar/own user/container) and documents the boundary ([PRD 06](06-security-baseline.md)). |
| **Acceptance** | An upstream authenticated call completes while a scan of config + env + transcript finds no secret; the reference pattern is documented for server authors and prepared for an **MCP ext-auth contribution** ([PRD 20](20-standards-and-claims.md)). |
| **Test** | `tests/test_stdio_virtualization.py`, `tests/test_stdio_no_token_passthrough.py`. |

### R9 — Just-in-time step-up issuance, approval-gated (P0)

| | |
|---|---|
| **Requirement** | A token **upgrade** into a higher-class scope (e.g., a prod-class credential) can be gated: the broker requests a decision; **agentpolicy** returns `ask`; a human approves; the broker mints the upgraded token with a tighter TTL and records `authorization.source`. |
| **Deny rule** | No approval → no upgrade → no credential. Timeout = deny (per agentpolicy). |
| **Acceptance** | A prod-scoped issuance cannot occur without an approving decision; the upgrade, approver, and provenance are in the ledger. |
| **Test** | `tests/test_stepup_approved.py`, `tests/test_stepup_denied.py`. |

### R17 — Secret-hygiene scanner & guided migration (P0 — the adoption unlock)

| | |
|---|---|
| **Requirement** | `agentkeys scan` finds **candidate secrets where agents can read them** — `.env` files, `mcp.json`/MCP server configs, harness settings, shell scripts, exported shell env — and `agentkeys migrate` moves a chosen secret into a backend and **rewrites every use site to a reference**, in one guided flow. |
| **Why it is P0** | The broker only helps credentials that have *left* the agent's world. Migration must be easier than pasting the key into a config — or nobody moves, and the invariant protects nothing. This is the feature that makes CUJ-1 a 15-minute journey instead of a project. |
| **Scan classes** | Known secret shapes (API keys, bearer tokens, private keys, connection strings, cloud credentials), config-embedded values, and **broad-reuse detection** — the same secret reused across many tools/servers (the blast-radius smell). |
| **Safety rules** | The scanner **never prints a found secret** (masked preview + file/field location only); nothing is auto-migrated; migrate is per-secret with confirmation; a failed migration leaves the original file untouched. |
| **Acceptance** | On a seeded fixture repo (fake secrets): scan finds **100% of planted candidates** with **0 printed secret values**; migrate moves one secret to the keychain and rewrites every use site; the original value is gone from the file and present nowhere except the backend. |
| **Test** | `tests/test_scan_candidates.py`, `tests/test_migrate_flow.py`; scenario SC-51. |
| **v0.1.x** | Reviewable patch/PR generation for teams (multi-file diffs), scheduled re-scans, CI mode. |

## B. Engineering requirements (E1–E15, all P0 for v0.1.0)

### E1 — Stable reference + issuance contract + idempotent ops

A small, versioned contract: a **reference** (`backend`, `path`, `class`, `scope-hint`) and an **issuance
record** (`reference_id`, `audience`, `tool`, `session_id`, `ttl`, `class`, `issued_at`, `expires_at`,
`binding`, `provenance`). Operations are **idempotent** keyed by reference+binding within a window: a retry
returns the same issuance and re-injects nothing new. *Acceptance:* duplicate issuance request returns the
same record; malformed references are rejected with a diagnostic naming the failing field.

### E2 — Durable broker store (single-writer) behind a capability-gated contract

One **BrokerStore** interface is the only way the core touches state: session state, issuance records,
revocations, and the ledger chain — with declared **capability flags** (`single_writer`, `durable`,
`atomic_issue`, `cluster_safe`) so the core **refuses configurations a driver cannot guarantee**. Driver:
SQLite (WAL) reference at v0.1.0; memory for tests. *Acceptance:* kill -9 mid-issue → restart recovers;
issuance is exactly-once per binding; a driver that cannot guarantee atomic single-use issuance is rejected
at load, never at runtime.

### E3 — Unforgeable, single-use, session-bound issuance

Every issuance is bound to a 128-bit secret stored **hashed**, tied to `reference_id` + `audience` + `tool`
+ `session_id`, expiring with the TTL, **single-use** per call, invalidated on revoke and on session end.
A replayed, forwarded, stale, or cross-bound issuance does nothing. *Acceptance:* replay/forward/stale/
cross-bound fixtures all fail closed and log `exchange-rejected` with reason.

### E4 — Fail-closed degradation, everywhere

Backend down/locked/ambiguous → deny issuance. Store down/corrupt → no new issuance, `doctor` non-zero.
Ledger sink down → local ledger remains authoritative with a gap marker. Export is read-only. **No path
from any failure to a credential.** *Acceptance:* fault-injection matrix (locked/absent backend, corrupt
store, sink offline, partial config) — every path is deny-or-pending, never allow, never silent.

### E5 — Redaction-by-default / never-log-secrets

A pattern + shape redactor (API keys, bearer tokens, private keys, connection strings, cloud creds) runs
**before** storage, rendering, export, and events; every redaction emits a **receipt** (field, class,
count). Raw secret values are never persisted anywhere. *Acceptance:* the evidence scanner finds **0**
secrets in store/export/ledger payloads; receipts present on every redacted field.

### E6 — Time correctness

All persisted times are UTC ISO-8601; TTLs use absolute instants + monotonic deltas. A backwards clock jump
cannot extend a TTL; a forwards jump cannot resurrect an expired issuance. *Acceptance:* clock-skew fixtures
behave fail-closed; expiry fires exactly once.

### E7 — Transport-agnostic egress-injection engine

One injection interface with drivers for **child-process environment** (stdio/CLI), **HTTP header**, and
**OAuth token exchange (RFC 8693)**; each driver resolves a reference, applies the binding, injects, and
forgets. *Acceptance:* conformance fixtures per driver; no driver can widen an audience or scope beyond the
binding.

### E8 — Harness adapters (below-the-harness by construction)

Because the broker operates below the harness, env/header interception generalizes; v0.1.0 ships named
**recipes for ≥2 Tier-1 harnesses** (Claude Code first), **all 5 by v0.3.0**, plus generic MCP clients and
custom SDKs. No single-harness build (REQUIRED — [PRD 19](19-harness-compatibility.md)). *Acceptance:*
each shipped recipe ends in a verified authenticated call for that harness.

### E9 — Pluggable backends behind a conformance-gated contract

One **Backend** interface: `resolve(reference) → secret`, `list`, `health`, with semantics every backend
MUST provide: never-log, resolve-at-use, fail-closed on ambiguity, and declared capability flags. Drivers:
keychain, credential-file (v0.1.0); 1Password/Vault/K8s/cloud SM (v0.1.x–v0.2.0); third-party via entry
points, admitted only by passing the conformance suite. *Acceptance:* a failing backend is rejected at load;
capability-failing configs refuse to start.

### E10 — Outside-the-agent control plane / tamper-resistance ("we are a target")

The broker is a **separate process** outside the agent's control plane; the agent cannot read its memory,
edit its config, or kill it silently. Config/hook integrity is checked at session start; tamper →
**fail-closed + loud event**. The broker holds secrets only transiently (keychain unlocked per-exchange).
*Acceptance:* tamper fixtures (edit config, kill broker, spoof reference) fail closed and alert.

### E11 — Versioning, migration, compatibility

The store schema is forward-compatible with a version table + migration path; the reference/issuance
contracts and event names are **stable within v0.x (additive only)**; events carry `event_version` per the
agentwatch schema process. *Acceptance:* an old store opens under a new binary (migrates or refuses
loudly); a 0.1.0 reference validates under 0.2.0.

### E12 — Observability + audit ledger + export/verify-log

Every lifecycle event lands in the local append-only hash-chained ledger and the agentwatch sink;
`agentkeys export --session/--reference` and `agentkeys verify-log` are first-class. *Acceptance:* the
ledger chain verifies; a tampered row is detected; export is deterministic and reproducible.

### E13 — Standards conformance as a gate (P0)

The product MUST pass the conformance suites for the standards it implements/aligns to (RFC 8693, 8707,
9700, 9728, 9068, 9449 where applicable; MCP authorization for HTTP egress; SPIFFE/WIMSE identifiers for
workload identity in v0.2.0). A conformance failure is a release blocker, and the conformance report is
published. Full mapping: [PRD 20](20-standards-and-claims.md). *Acceptance:* the conformance report is
green on the release commit; unsupported standards are labeled, not implied.

### E14 — No token passthrough; audience enforced at egress (P0)

The broker never forwards a client token upstream (MCP security best practices); it mints a
broker-scoped, audience-bound credential for the target. The egress injector enforces the audience even if
a downstream fails to. *Acceptance:* the token-passthrough fixture shows the upstream receives a
broker-minted token, never the client's.

### E15 — Supply-chain integrity (P0, non-negotiable for a security product)

Signed releases (Sigstore), SLSA provenance, pinned deps, SBOM (CycloneDX/SPDX), OpenSSF Scorecard A,
`security.txt`, CVE/coordinated-disclosure program, and OSS-Fuzz for parsers (reference grammar,
JSON-RPC/MCP frames). Given Plugin4Shell was a **supply-chain attack on coding agents**, our own supply
chain is demonstrably clean. *Acceptance:* badges/attestations present; the vuln policy is live; fuzz
targets run in CI.

## C. Feature catalog (v0.1.0)

| # | Feature | Requirement |
|---|---|---|
| F1 | Reference model + `.env`-to-reference migration helper | R1, E1 |
| F2 | Egress injector: env-virtualization (stdio/CLI) | R2, E7 |
| F3 | Egress injector: HTTP header | R2, E7 |
| F4 | Egress injector: OAuth RFC 8693 token exchange | R2, R3, E7 |
| F5 | Token minting with TTL + audience + tool + session bindings | R3, E3 |
| F6 | `agentkeys revoke <agent\|session\|all>` + kill-time harness | R4 |
| F7 | Backends: OS keychain, credential file (+ conformance suite) | R5, E9 |
| F8 | Fail-closed engine + `agentkeys doctor` | R5, E4 |
| F9 | Ledger (hash chain) + agentwatch event emitter | R6, E12 |
| F10 | `agentkeys export` / `agentkeys verify-log` | R6, E12 |
| F11 | Secret-evasion detector + enforce hooks | R7, E10 |
| F12 | **stdio MCP virtualization** (launch wrapper + placeholder) | R8, E7 |
| F13 | Step-up issuance via agentpolicy `ask` | R9, E3 |
| F14 | Redactor + receipts | E5 |
| F15 | Broker store (SQLite) + capability flags | E2 |
| F16 | Config: backends, TTLs per class, bindings, enforce mode | R5 |
| F17 | Harness recipes (≥2 Tier-1 at v0.1.0) | E8 |
| F18 | Conformance kit + `agentkeys conformance` | E13 |
| F19 | Context-dump + revocation attack packs | R1, R4 |
| F20 | SDK / stable CLI contract for embedders | E1, E9 |
| F21 | `agentkeys scan` + `agentkeys migrate` (secret-hygiene migration) | R17 |
| F22 | `agentkeys posture` (credential posture report) | R18 |
| F23 | Canary references + high-severity page (agenthalt composition optional) | R19 |

## D. Forward slate (P1/P2 — scheduled, not built)

| # | Requirement | Pri | Notes |
|---|---|---|---|
| **R10** | **Enterprise/cloud backends** — 1Password, HashiCorp Vault, K8s Secrets, AWS/GCP/Azure secret managers | P1 | same Backend contract; conformance-gated |
| **R11** | **Server / HA / fleet broker mode** — a central broker for many agents; parent→child delegation with monotonic narrowing | P1 | Entra does parent-child; OSS has nothing |
| **R12** | **SPIFFE/WIMSE workload identity** — SVIDs (JWT/X.509/WIT) for server-side agents; agent identity attestation joined to `gen_ai.agent.id` | P1 | Aembit's shape, OSS-ified; aligns with IETF AIMS |
| **R18** | **Credential posture report** — `agentkeys posture`: env-resident secrets, references by backend/class, TTL config vs observed, revocations per agent, **unbrokered MCP servers**; terminal + JSON, secret-free | P1 | the ecosystem PRD's "credential health reports" (its R12); makes the migration funnel visible |
| **R13** | **Blast-radius budgets** — cumulative capability caps (≤N files, ≤M sends, ≤$X per session); exhaustion auto-halts via agenthalt | P2 | novel; nothing ships it |
| **R14** | **Sender-constrained tokens (DPoP, RFC 9449)** — prove possession so a stolen token string is not enough | P2 | the gap Ping explicitly named |
| **R15** | **MCP-server attestation/reputation feed** — signed tool descriptions + community poisoning reports | P2 | detection (agent-scan) minus reputation |
| **R16** | **Egress taint/DLP** — tag tool outputs containing secrets/PII; deny their flow to external sinks | P2 | simplified Pillar taint analysis |
| **R19** | **Canary references (broker-native honeytokens)** — the broker registers decoy references that look identical to real ones; any resolution/use attempt is an attacker-in-context signal: immediate high-severity page, the attempt is recorded with full attribution, and (composed with agenthalt, which owns the decision) it can auto-trigger `revoke` | P2 | detection a detector cannot fake: the *only* way a canary fires is someone actually trying to use a stolen-looking credential; Thinkst's canarytoken pattern, made broker-native; separation of duties preserved — we expose the trigger, agenthalt decides |

## E. Standards & compliance (summary — full mapping in [PRD 20](20-standards-and-claims.md))

**Implemented / aligned:** RFC 8693 (token exchange), RFC 8707 (resource indicators / audience), RFC 9700
(OAuth security BCP), RFC 9728 (protected-resource metadata), RFC 9068 (JWT access tokens), RFC 9449 (DPoP,
v0.3.0), OAuth 2.1 / PKCE (RFC 7636), MCP authorization (HTTP egress) + a proposed **stdio-credential
ext-auth contribution**, SPIFFE/WIMSE + the IETF **AIMS** draft (v0.2.0), OTel GenAI semantic conventions
(spans), Cedar (via agentpolicy). **Frameworks aligned:** OWASP LLM Top 10 2025 (LLM02, LLM06),
OWASP Agentic AI Top 10 (identity confusion, excessive agency), NIST AI RMF / NIST AI 600-1, NIST SP
800-207 (zero trust), MITRE ATLAS, ISO/IEC 42001, EU AI Act Art. 14 (human oversight), CSA NHI guidance.
**Own reliability ladder:** `security.txt`, CVE program, SLSA/Sigstore, SBOM, OpenSSF Scorecard, OSS-Fuzz,
SOC 2 Type I→II roadmap. **Claim labels:** *documented · conformance · field-tested · verified* — no claim
above its evidence.

## F. What is deliberately small

No credential **creation/rotation** (the IdP is the source of truth — we broker, never mint long-lived
secrets); no browser/session credential capture (permanent refusal); no policy engine (agentpolicy); no
enforcement in the harness (the enforcer); no dashboard; no multi-tenant SaaS/multi-node in v0.1.0 (server
mode is R11); no secret **storage** (backends store). Full list in [PRD 14](14-non-goals.md).

## G. Requirement priority table

| Req | Title | Pri | Req | Title | Pri |
|---|---|---|---|---|---|
| R1 | Reference-only context | P0 | E1 | Reference + issuance contract | P0 |
| R2 | Egress injection at use | P0 | E2 | Durable broker store | P0 |
| R3 | Token bindings | P0 | E3 | Unforgeable single-use issuance | P0 |
| R4 | Revoke ≤1s | P0 | E4 | Fail-closed everywhere | P0 |
| R5 | Keychain + file backends | P0 | E5 | Redaction-by-default | P0 |
| R6 | Lifecycle events + ledger | P0 | E6 | Time correctness | P0 |
| R7 | Secret-evasion detection | P0 | E7 | Egress-injection engine | P0 |
| R8 | **stdio MCP virtualization** | P0 | E8 | Harness adapters | P0 |
| R9 | Step-up issuance | P0 | E9 | Pluggable backends | P0 |
| R10 | Cloud/enterprise backends | P1 | E10 | Outside-the-agent control plane | P0 |
| R11 | Server/HA/fleet mode | P1 | E11 | Versioning + compatibility | P0 |
| R12 | SPIFFE/WIMSE identity | P1 | E12 | Ledger + export/verify-log | P0 |
| R13 | Blast-radius budgets | P2 | E13 | Standards conformance gate | P0 |
| R14 | DPoP sender-constrained | P2 | E14 | No token passthrough | P0 |
| R15 | MCP attestation feed | P2 | E15 | Supply-chain integrity | P0 |
| R16 | Egress taint/DLP | P2 | R17 | Secret-hygiene scan + migration | P0 |
| R18 | Credential posture report | P1 | R19 | Canary references | P2 |
