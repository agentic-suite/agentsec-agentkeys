# PRD 11 — Decisions

**BLUF:** agentkeys is shaped by a small set of **frozen decisions** — choices that other documents,
design docs, tests, and the WBS are all built on, and that we do not re-litigate per feature. They are
frozen because each one removes a class of failure rather than a single bug: *the broker brokering and
never storing* keeps the crown jewels out of our own database; *below the harness* makes the credential
model generalize instead of fragmenting; *fail closed* makes an outage a denial and never a grant; *explicit
revocation* makes "stop it now" a command instead of a rotation project. This document records each
decision with the **why** and the **alternatives rejected**, plus a table of **deferred decisions with
defaults** for the choices we have deliberately not made yet. It is the tie-breaker for design arguments:
if a proposal contradicts a frozen decision, the proposal is wrong by default.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## How to read this document

- **Frozen (D-01…D-17)** — decided for v0.1.0 and the shape of the product; changing one is a design-doc
  change with a migration note, not a ticket.
- **Deferred** — decided *to defer*, with a stated default and a trigger to revisit. Deferred is not
  "undecided"; the default applies until the trigger fires.
- Priorities and requirements referenced here are defined in [PRD 05](05-features.md); security invariants
  in [PRD 06](06-security-baseline.md); the honest refusals that follow from these decisions in
  [PRD 14](14-non-goals.md). Each decision is expected to become an ADR; where an ADR numbers itself, the
  id below is the stable cross-reference.

---

## Frozen decisions

### D-01 — The broker brokers; it never stores or vaults secrets

- **Decision:** agentkeys **never** becomes the store of record for a secret. It resolves a reference from
  an external backend (OS keychain, credential file, later 1Password/Vault/K8s/cloud SM), injects it at
  egress, and forgets it. The broker's database holds references, bindings, and lifecycle events — never
  secret bytes. ([PRD 05](05-features.md) R1, R5, E5.)
- **Why:** the product's whole promise is that compromising the agent yields nothing. If we also held the
  plaintext, we would re-introduce the exact single point of theft we exist to remove, and we would be a
  vault with a worse story. "Your secrets stay where they are" is also the adoption path: point it at the
  vault you already trust.
- **Alternatives rejected:** *ship an embedded encrypted store* (a second vault, bigger target, migration
  burden); *cache secrets in the broker for speed* (violates never-in-context durability and turns an
  outage into theft); *hold secrets only in the broker's memory* as the source of truth (still the store of
  record; keychain-unlock-per-exchange is the intended transient model).

### D-02 — Never mint long-lived secrets

- **Decision:** every credential agentkeys hands out is **short-lived, audience-bound, tool-scoped, and
  session-bound** (R3, E3). We do not create standing API keys, do not rotate the org's secrets, and do not
  issue tokens that outlive a session.
- **Why:** the org's IdP / secret manager is the source of truth. Duplicating issuance creates a second
  authority to reconcile, and any long-lived secret we mint becomes exactly the static, over-scoped key the
  product is designed to delete. Short TTL + binding is the one defense class nearly every reviewer accepts.
- **Alternatives rejected:** *manage the secret lifecycle for users* (we would own rotation and the blame);
  *long-lived broker tokens with revocation only* (a leaked token is live until an operator notices);
  *dynamic secrets in v0.1.0* (a backend/IdP capability, not a broker primitive — see D-16).

### D-03 — Below the harness, not per-harness

- **Decision:** the credential model lives **underneath** the agent harness. Interception is by egress
  transport (child-process environment, HTTP header, OAuth exchange), not by a Claude-Code- or
  Cursor-specific hook. Named **recipes** ship for ≥2 Tier-1 harnesses at v0.1.0 and all 5 by v0.3.0, but
  there is no single-harness build (E8; [PRD 19](19-harness-compatibility.md)).
- **Why:** a broker that only works inside one harness is not a broker — it is a plugin, and it dies when
  the harness changes. Egress interception generalizes across harnesses, MCP clients, and custom SDKs, and
  it is the layer platforms structurally will not build and gateways cannot reach.
- **Alternatives rejected:** *per-harness plugins as the primary integration* (fragmentation, N× surface);
  *a single-harness first release* (explicitly disallowed by E8); *gateway-only brokering* (cannot see local
  stdio subprocess environments or a CLI reading a credential file).

### D-04 — References are opaque and safe to log

- **Decision:** an agent-visible reference is an **opaque handle** (`akref:<backend>/<path>`, `op://…`, a
  local handle). It carries no secret bytes, is resolvable only by the broker, is scoped by backend policy,
  and is designed to be printed, serialized, and logged.
- **Why:** if the reference is the only credential-shaped thing in the agent's world, then a context dump
  is a dump of handles — safe by construction. This is what turns "don't leak the key" from a discipline
  into a property (R1).
- **Alternatives rejected:** *put a short-lived token in context* (still usable if stolen within its TTL);
  *embed a hash of the secret in the reference* (a verification oracle); *make references guessable*
  (enables enumeration/spoofing — see E10 tamper fixtures).

### D-05 — Egress injection over MITM-by-default (three drivers)

- **Decision:** inject at egress with three reference-driven drivers — **(a)** child-process environment
  virtualization (stdio MCP/CLI), **(b)** HTTP header injection, **(c)** OAuth RFC 8693 token exchange.
  We do **not** default to a man-in-the-middle proxy that terminates TLS for every connection.
- **Why:** (1) **Local-first** — a proxy needs a trust boundary and a CA the user installs; the local
  cases (a stdio server's env, a CLI's file) never traverse the network at all. (2) **Least surprise** —
  three narrow, contract-tested drivers are auditable where a transparent MITM is an opaque blob of every
  secret crossing the wire. (3) **Composability** — we can adopt an enterprise gateway later as *one more
  egress point* without rewriting the core.
- **Alternatives rejected:** *transparent MITM proxy as the primary shape* (cert distribution, breakage,
  and it cannot reach the local cases); *header rewrite only* (misses stdio and non-HTTP tools);
  *in-process SDK hooks only* (requires changing every agent).

### D-06 — Fail closed by default

- **Decision:** any backend that is unavailable, locked, ambiguous, or partially configured **denies
  issuance**. Any store that is down or corrupt yields no new issuance. A ledger sink that is offline
  leaves the local ledger authoritative with a gap marker. There is **no path from any failure to a
  credential** (E4, R5).
- **Why:** the failure semantics of a security control are its real semantics. A broker that degrades to a
  static secret or an env fallback under stress is worse than no broker, because it launders an outage into
  a silent, unbound grant. Deny is the only safe default.
- **Alternatives rejected:** *best-effort resolution with a warning* (a warning is not a control);
  *env/static fallback for availability* (re-creates C1); *"fail open but alert"* (alerts arrive after the
  exfiltration).

### D-07 — Revocation is explicit and unconditional; TTL is defence in depth

- **Decision:** `agentkeys revoke <agent|session|all>` invalidates broker session state so the **next
  exchange refuses** and session-bound issued tokens stop authenticating — measured end-to-end **≤1s** and
  replay-verified continuously in CI (R4). Revocation is **never** gated on policy and **never** dependent
  on TTL expiry.
- **Why:** the spine CUJ-2 exists because race-the-rotation is the observed failure. Short TTLs shrink the
  window but cannot stop an adversary who acts inside it. A kill switch that has to ask permission is not a
  kill switch, which is why revocation is the one action that bypasses policy.
- **Alternatives rejected:** *TTL-only expiry* (the window is the incident); *policy-gated revocation*
  (adds latency and an approval to an emergency); *network-level kill only* (misses local/air-gapped);
  *revoke-requires-restart* (cannot be done under fire).

### D-08 — SQLite single-writer is the reference broker store

- **Decision:** the core touches state only through one **BrokerStore** contract; the v0.1.0 reference
  driver is **SQLite in WAL mode** (single writer), with an in-memory driver for tests. The contract
  declares capability flags (`single_writer`, `durable`, `atomic_issue`, `cluster_safe`) and the core
  **refuses** a configuration a driver cannot guarantee (E2).
- **Why:** correctness first — the store must give exactly-once single-use issuance and crash-safe
  recovery (kill -9 mid-issue), and a single-writer embedded store gives that with no operational
  dependency. Capability flags keep the choice honest: a driver that cannot promise atomic issuance is
  rejected at **load**, not at runtime.
- **Alternatives rejected:** *a network database in v0.1.0* (an ops dependency for a local-first tool);
  *plain files as the store* (no transactions, no recovery); *pluggable-but-unchecked drivers* (a driver
  that silently weakens single-use issuance — the exact gap the flags close).

### D-09 — The lifecycle ledger is append-only and hash-chained

- **Decision:** every issuance/use/upgrade/revocation/exchange-rejection/evasion is an append-only entry in
  a local **hash-chained** ledger and an **agentwatch-schema** event; `verify-log` confirms the chain and
  `export` emits a deterministic timeline (R6, E12).
- **Why:** an auditor must be able to *trust* the record, not just read it. A hash chain makes tampering
  **detected rather than silently accepted** (invariant I8), and joining by `session_id` links the
  credential lifecycle to the session trace Dana already has.
- **Alternatives rejected:** *mutable log + external signatures only* (no local tamper-evidence);
  *telemetry-only, no local record* (air-gapped and offline cases lose their evidence); *remote-first
  ledger* (network dependency, privacy, and the sink-offline case).

### D-10 — Step-up decisions go to agentpolicy; we never decide policy ourselves

- **Decision:** when a token upgrade needs authorization, the broker **asks** — `agentpolicy` returns a
  decision (e.g. `ask`); a human approves; the broker mints the upgraded token with a tighter TTL and
  records `authorization.source`. No approval → no credential; timeout → deny (R9).
- **Why:** the ecosystem has one decision boundary: policy is a different product with a different threat
  model, language (Cedar), and lifecycle. A broker that also decided policy would duplicate the boundary,
  drift from it, and put the crown jewels behind a hand-rolled rule engine.
- **Alternatives rejected:** *embed a policy engine* (boundary collapse — the thing that holds secrets must
  not be the thing that decides, per [PRD 06 §3]); *no step-up at all* (prod scope would be ambient);
  *hard-coded approval list in the broker* (unversioned, unauthorized, ungovernable).

### D-11 — stdio virtualization works across a process boundary (with an honest limit)

- **Decision:** local **stdio MCP servers** are launched **under the broker** with references/placeholders
  instead of real values; the broker supplies a scoped token at egress (R8). The broker requires a
  **protected process boundary** (sidecar / own user / container) and **documents** that a process sharing
  the same readable runtime as arbitrary agent code cannot be fully protected.
- **Why:** the MCP spec tells stdio servers to read credentials from the environment — the exact vector
  behind documented incidents and **unowned by everyone** (coverage row #8). Moving the credential across a
  process boundary is the strongest honest answer; claiming more would be a lie we would be caught in.
- **Alternatives rejected:** *rewriting every server to call the broker in-process* (impossible at scale);
  *env-placeholder only with no boundary* (the co-located process can read the runtime); *claiming full
  protection* (dishonest — [PRD 06 §4](06-security-baseline.md)).

### D-12 — Local-first; no cloud requirement

- **Decision:** v0.1.0 is a local broker process + CLI + local store + local ledger. **No** SaaS tenant,
  network trust boundary, or third-party account is required; it works air-gapped (R5, E4, E12; CUJ-11).
- **Why:** the same semantics must serve a solo developer and an air-gapped enterprise. A cloud dependency
  would add a place to leak, a place to be down, and a procurement conversation before the first tool call.
  Server/HA mode is roadmap (R11) and is additive, not a prerequisite.
- **Alternatives rejected:** *cloud control plane as the default* (fails the air-gap and solo cases);
  *local-with-telemetry-upload* (privacy and egress); *network-only revocation* (breaks D-07 for local
  sessions).

### D-13 — Additive contracts only

- **Decision:** the reference/issuance contracts, the event vocabulary, and the store schema are **stable
  within v0.x and extended additively** — fields are added, never renumbered or repurposed; events carry
  `event_version` per the agentwatch schema process (E11).
- **Why:** a broker is embedded and depended upon; silent contract changes break every integration and every
  ledger consumer at once. Additive-only keeps a 0.1.0 reference valid under 0.2.0 and lets old stores
  migrate or refuse **loudly**.
- **Alternatives rejected:** *free schema evolution* (breaks the ecosystem); *compatibility breaks behind a
  major-version flag* (even major breaks cost integrators); *versioned duplicate APIs* (parallel
  implementations that drift).

### D-14 — No token passthrough

- **Decision:** the broker **never** forwards a client-supplied token upstream. For every target it mints a
  broker-scoped, audience-bound credential, and the egress injector enforces the audience even if the
  downstream fails to (E14; MCP security best practices).
- **Why:** passthrough is the anti-pattern the MCP spec names — it reuses a token against a server it was
  not meant for and dissolves the audience binding that kills confused-deputy replay. The whole value of
  the broker is that the upstream sees a token the broker chose.
- **Alternatives rejected:** *forward the token for simplicity* (re-creates C3); *forward only when the
  audience is "close"* (a heuristic in a binding check is not a binding); *let the downstream decide*
  (defense in depth means we enforce regardless).

### D-15 — Sender-constrained tokens (DPoP) deferred to R14

- **Decision:** v0.1.0 issues **bearer** tokens; **DPoP (RFC 9449)** is enumerated as **R14 (P2,
  v0.3.0+)** and is **not** claimed as done (E13; [PRD 20](20-standards-and-claims.md)).
- **Why:** DPoP is real defense in depth against a stolen token *string*, but it requires the egress
  driver and the resource server to both speak it; shipping it half-supported would be worse than labeling
  the gap. Bearer + binding + short TTL covers v0.1.0.
- **Alternatives rejected:** *claim DPoP in v0.1.0* (false conformance — a labeled non-claim is the honest
  move); *mTLS/private-key-JWT as the v0.1.0 answer* (different deployment constraints, same deferral
  logic).

### D-16 — Enterprise/cloud backends deferred to R10

- **Decision:** v0.1.0 ships **OS keychain + credential-file** backends only, behind a pluggable,
  conformance-gated contract (E9). 1Password, Vault, K8s Secrets, and cloud secret managers are **R10
  (P1)**.
- **Why:** two well-understood backends prove the contract and the fail-closed semantics; adding five
  vendors before the contract is frozen would freeze the wrong contract. Third-party backends are admitted
  only by passing the conformance suite, so the ecosystem can extend us without forking us.
- **Alternatives rejected:** *ship Vault first* (an ops dependency and a different failure model before the
  core is proven); *one hard-coded backend* (no path for embedders); *accept any backend plugin*
  (capability-failing backends weaken fail-closed — the flags reject them at load).

### D-17 — Shared-session / multi-agent semantics: deny ambient, delegate explicitly, narrow monotonically

- **Decision:** a session binds to **exactly one agent identity** (v0.1.0). There is **no implicit
  inheritance**: two agents may reference the *same backend secret*, but only through **separate
  references, separate sessions, and independent bindings and revocation domains**. When delegation
  arrives with **R11**, it is **explicit only** and **monotonically narrowing** — a child issuance can
  never exceed its parent's audience/tool/class — with **separate revoke domains**: revoking a child never
  kills the parent; revoking the parent **cascades** to children.
- **Why:** the ecosystem PRD left "multiple agents, one user credential — inherit, split, or deny?" open.
  Ambient inheritance is standing privilege with extra steps: it is unattributable, unkillable per-agent,
  and exactly the failure the product exists to remove. Deny-by-default is the only answer consistent with
  zero standing privilege; explicit delegation gives teams a governed path when they need one.
- **Alternatives rejected:** *implicit inheritance* (ambient authority, per-agent revocation impossible);
  *automatic splitting* (the broker guessing scope — a heuristic in a binding check, D-14); *one shared
  session* (an audit trail that cannot attribute an action to an agent); *deny delegation entirely*
  (forever — refused: R11 needs it, and "explicit + narrowing + separate domains" is governable).

---

## Deferred decisions (with defaults)

Deferred does **not** mean undecided; the default applies until the trigger fires. Changing a default is a
design-doc change, not a ticket.

| # | Deferred question | Default until decided | Trigger to revisit | Refs |
|---|---|---|---|---|
| DD-01 | Windows support | **Not yet** — macOS + Linux first | measured demand / a Tier-1 harness user base on Windows | [PRD 03 §4](03-landscape.md) |
| DD-02 | Server / HA / fleet broker | **Not yet** — single-user local broker | multi-agent fleet adoption; R11 | [PRD 05 §D](05-features.md) |
| DD-03 | Multi-tenant / SSO / SCIM / directory sync | **Refused in phase** — local single-user | enterprise deployment of R11 | [PRD 14](14-non-goals.md) |
| DD-04 | A GUI / dashboard | **CLI + local ledger** | recurring operator demand for a viewer | [PRD 03 §4](03-landscape.md) |
| DD-05 | Log retention / WORM storage | **Local append-only ledger**, operator-managed retention | compliance requirement (SOC 2 Type II / ISO 27001) | [PRD 20 §5](20-standards-and-claims.md) |
| DD-06 | Ledger hash algorithm | **SHA-256 chain** (FIPS-mode uses OS-native crypto) | FIPS-mode target; algorithm agility work | E12, E15 |
| DD-07 | Token signing algorithm | **Algorithm-agile, pinned per config**; reference JWT profile per RFC 9068 | interop target that requires a specific alg | E13, [PRD 20](20-standards-and-claims.md) |
| DD-08 | Browser/session credential capture | **Permanent refusal** | never (an anti-feature) | [PRD 14](14-non-goals.md) |
| DD-09 | ML in the enforcement path | **Permanent refusal** — deterministic only | never | [PRD 14](14-non-goals.md) |
| DD-10 | Proprietary token format | **Permanent refusal** — standards only | never | [PRD 14](14-non-goals.md), [PRD 20](20-standards-and-claims.md) |
| DD-11 | DPoP / sender-constrained tokens | **Bearer until R14** | R14 (v0.3.0+) | D-15, [PRD 20](20-standards-and-claims.md) |
| DD-12 | Cloud / enterprise backends | **Keychain + file only** | R10 (v0.1.x–v0.2.0) | D-16 |
| DD-13 | SPIFFE/WIMSE workload identity | **Not yet** (identity consumed, not issued) | R12 (v0.2.0) | [PRD 20 §2](20-standards-and-claims.md) |
| DD-14 | Egress taint / DLP on tool output | **Not yet** | R16 (v0.3.0+) | [PRD 05 §D](05-features.md) |
| DD-15 | MCP ext-auth contribution filing | **Prepared in-repo, not yet filed** | reference pattern + fixtures + threat appendix complete | [PRD 20 §3](20-standards-and-claims.md) |

## Decision status

| State | Meaning |
|---|---|
| **Frozen (D-01…D-17)** | Decided for v0.1.0; a change requires a design-doc change and a migration note. |
| **Deferred (DD-01…DD-15)** | A decision to defer; the stated default applies until the trigger fires. |
| **Refused permanently (DD-08…DD-10)** | Not a deferral — the ecosystem boundary requires the refusal. See [PRD 14](14-non-goals.md). |

**Honesty note:** these are **documented** decisions (label *documented* per [PRD 20 §6](20-standards-and-claims.md));
none is *field-tested*. A decision being frozen makes the design arguable, not the implementation proven.
Where a decision depends on an unbuilt capability (stdio boundary, step-up via agentpolicy, the ledger
chain), the honest statement is that the behavior is the **design of record** and the corresponding
scenario in [PRD 17](17-scenarios.md) is the evidence path once executed.
