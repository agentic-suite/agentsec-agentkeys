# PRD 04 — Users, User Stories & Critical User Journeys

**BLUF:** agentkeys has four humans at the center — the **agent owner** who wants safe autonomy, the
**security engineer** who owns the credentials and the audit, the **SRE/incident commander** who must kill
access *now*, and the **auditor** who must reconstruct what happened — plus the **MCP server author** and
the **agent platform builder** who integrate it. The acceptance spine is one measurable moment: *a full
context dump of the agent yields zero usable credentials, and `revoke` lands in under a second.* Every CUJ
below either contributes to that moment or to the evidence that it happened.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Personas

| ID | Persona | Context | Primary need | What failure looks like to them |
|---|---|---|---|---|
| **P1** | **Maya — agent platform engineer** | Runs coding/research agents for a small team; owns agent adoption and the incident when it goes wrong | Let agents do real work while the secrets stay out of reach and revoked in one command | She is the permanent rotation bottleneck; or an agent exfiltrates a prod key during a meeting |
| **P2** | **Ravi — security engineer** | Owns credential policy, detection/response, and the audit story; agent activity is a new blind surface | Credentials that are bound, revocable, and evidenced in the tools he already runs | A leaked key means a quarter of rotation; he cannot prove what the agent could reach |
| **P4** | **Sam — solo developer / indie** | One machine, personal keys, 2–3 harnesses | Five-minute setup, sane safe defaults, no cloud account | He pastes a key into `mcp.json`, leaks it once, and never installs a security tool again |
| **P5** | **Alex — agent platform builder (embedder)** | Builds agents on LangChain/MCP/custom stacks; needs embeddable controls | An SDK/broker that makes his product "security-review-ready" in a day | He hand-rolls credential handling and ships a leak |
| **P3** | **Dana — compliance / GRC lead** | Owns SOC 2 / ISO 42001 / EU AI Act Art. 14 evidence for the AI stack | Auditable, continuous proof of credential controls, joined to the session trace | A log line that says "used a credential" with no binding, principal, or revocation record |
| **S1** | **Jordan — SRE / incident commander** | Gets paged; must stop a misbehaving agent *now* | One command (or one API call) that makes all of an agent's access dead in ≤1s | "We couldn't stop it" — the sentence in every agent postmortem |
| **S2** | **Priya — MCP server author** | Ships a local stdio MCP server that calls real APIs | A documented, standard way to receive a scoped credential without embedding it in config | Users hardcode a broad, long-lived key into her server's config |

## 2. User stories (v0.1.0)

### Agent owner (Maya)

| ID | Story | Acceptance |
|---|---|---|
| **US-01** | As an agent owner, I want my agent to hold a reference instead of a secret, so a prompt injection that dumps the context gets nothing | Context-dump pack finds zero usable credentials |
| **US-02** | As an agent owner, I want the broker to inject the real credential at the moment of use, so the agent authenticates without ever seeing it | Real authenticated tool call completes; transcript contains only the reference |
| **US-03** | As an agent owner, I want to bind a token to one server, one tool, and one session, so a stolen token is useless elsewhere | Replay against another audience/tool/session fails |
| **US-04** | As an agent owner, I want one command to kill all of an agent's access, so I do not race a rotation project | `revoke` replay-verified ≤1s |
| **US-05** | As an agent owner, I want to rotate a backend secret without restarting the agent, so rotation is routine | Post-rotation call succeeds; agent never restarts |
| **US-06** | As an agent owner, I want a misconfigured or unavailable backend to **deny**, so an outage is never an accidental grant | Backend down → issuance denied, no static fallback |

### Security engineer (Ravi)

| ID | Story | Acceptance |
|---|---|---|
| **US-07** | As a security engineer, I want every issuance/use/upgrade/revocation recorded, so I can prove what an agent could reach | Lifecycle events emitted; ledger chain verifies |
| **US-08** | As a security engineer, I want attempts to read raw credentials outside the broker flagged, so evasion is visible | `.env`/cloud-cred/keychain read → high-severity event |
| **US-09** | As a security engineer, I want high-risk credentials to require an approval to be upgraded into, so prod scope is never ambient | Step-up issuance without approval → denied |
| **US-10** | As a security engineer, I want the broker to fail closed and prove it, so I can trust the invariant | Fault-injection: every failure path is deny-or-pending |
| **US-11** | As a security engineer, I want a reproducible benchmark I can re-run, so the vendor's claim is not faith | Public attack pack + kill-time benchmark reruns green |
| **US-12** | As a security engineer, I want to see the backend matrix and failure semantics, so I know what is supported | Documented backend matrix; `doctor` explains effective config |
| **US-28** | As a security engineer, I want a posture report of what agents can reach, so residual risk is visible without a spreadsheet | `agentkeys posture` enumerates env-resident secrets, unbrokered MCP servers, revoke counts — zero secret material in the output |

### SRE / incident commander (Jordan)

| ID | Story | Acceptance |
|---|---|---|
| **US-13** | As an incident commander, I want to kill one agent, one session, or everything, so I can scope the kill | `revoke <agent\|session\|all>` honored |
| **US-14** | As an incident commander, I want the kill to be immediate, not "when the token expires", so the blast radius stops now | Next exchange refuses; issued tokens stop authenticating |
| **US-15** | As an incident commander, I want the revocation to be an event with the operator identity, so the response is auditable | `revoked` event carries principal + target + timestamp |

### MCP server author (Priya)

| ID | Story | Acceptance |
|---|---|---|
| **US-16** | As an MCP server author, I want my stdio server to receive a scoped credential at call time, so users stop hardcoding a broad key | Server authenticates; config/env contain no real secret |
| **US-17** | As an MCP server author, I want a documented reference pattern, so I can adopt it without a custom broker | Documented stdio recipe; reference → resolve at egress |
| **US-18** | As an MCP server author, I want no token passthrough, so a client token cannot be replayed upstream | Upstream gets a broker-minted scoped credential, not the client token |

### Compliance / auditor (Dana)

| ID | Story | Acceptance |
|---|---|---|
| **US-19** | As an auditor, I want the credential lifecycle reconstructable per session, so I can see who/what/when | `export --session` timeline; every transition attributed |
| **US-20** | As an auditor, I want the ledger to be tamper-evident, so I can trust it | Hash chain verifies; a corrupted row is detected |
| **US-21** | As an auditor, I want to know the audience/tool/session binding of every issuance, so scope is provable | Binding fields present on every event |

### Embedder (Alex)

| ID | Story | Acceptance |
|---|---|---|
| **US-22** | As an embedder, I want a stable broker contract + SDK/CLI, so I can wire any stack without a fork | Versioned contract + fixture; end-to-end from a sample app |
| **US-23** | As an embedder, I want a pluggable backend, so I keep my own secret store | Backend interface + conformance; my backend passes |
| **US-24** | As an embedder, I want the same broker across my harnesses, so I do not build per-harness credential code | One broker, two+ harness recipes, no per-harness fork |

### Solo developer (Sam)

| ID | Story | Acceptance |
|---|---|---|
| **US-25** | As a solo dev, I want install → first brokered call in ≤15 minutes with no code change, so I actually adopt it | Field test: median < 15 min |
| **US-26** | As a solo dev, I want sane safe defaults and no cloud account, so the tool never becomes the risk | Monitor-safe default, fail-closed, works offline |
| **US-27** | As a solo dev, I want `agentkeys` to find the secrets my agent can read and walk me through moving them, so adoption takes minutes, not a project | Scan finds planted candidates in the fixture repo (masked previews, 0 printed values); migrate moves one secret end-to-end; re-scan shows it gone |

## 3. Critical User Journeys

Each CUJ lists the **trigger**, the **happy path**, the **unhappy paths that must be designed**, the
**requirements exercised**, and the **acceptance signal**.

### CUJ-1 — First brokered credential in 15 minutes (P4 Sam)

- **Trigger:** Sam installs agentkeys and runs an agent whose tool needs a credential.
- **Path:** `pip install` → `agentkeys init` writes a minimal config (keychain backend, monitor-safe) →
  `agentkeys scan` flags the keys in Sam's `.env`/MCP config (masked previews, file/field locations) →
  `agentkeys migrate` moves one into the keychain and rewrites every use site to a reference → the agent's
  tool call authenticates via the broker → Sam sees a lifecycle event. **No change to the agent's code.**
- **Unhappy:** no keychain available → credential-file backend with a loud `doctor` warning · backend
  locked → fail closed with an actionable error, never a silent env fallback · malformed reference →
  rejected with a diagnostic naming the field.
- **Requirements:** R1, R2, R5, R17, E1, E7. **Acceptance:** median time install → first recorded brokered
  call **< 15 min** in the field test; no cloud dependency.

### CUJ-2 — Revoke in one second under fire (S1 Jordan) — **the spine**

- **Trigger:** an agent is exfiltrating or misbehaving mid-session; Jordan is paged.
- **Path:** `agentkeys revoke --agent <id>` (or `--session`/`--all`) → broker session invalidated → the
  **next exchange refuses**, and tokens issued to that session stop authenticating → `revoked` event with
  operator identity → Jordan re-runs the exfil attempt and it fails.
- **Unhappy:** revoke during an in-flight call → the call's next hop fails closed · revoke for an unknown
  target → error, never a silent no-op · broker process down → revoke is still possible via the CLI's
  direct store/`all` path (documented), and `doctor` says so.
- **Requirements:** R4, E3, E6. **Acceptance:** measured end-to-end (issue → revoke → replay fails)
  **≤1s**, verified continuously in CI, not only at launch.

### CUJ-3 — Context-dump finds zero credentials (P2 Ravi) — **the invariant**

- **Trigger:** a simulated compromise dumps the agent's entire context (transcript, env, args, config,
  logs).
- **Path:** the attack pack scans every artifact for anything usable → **zero real credentials** →
  only references and clearly-fake test values → report published.
- **Unhappy:** a backend value leaked into an argument or a log → **the pack fails the build** (not a
  warning); redaction receipts prove where masking happened.
- **Requirements:** R1, R2, R7, E5. **Acceptance:** context-dump pack finds **0 usable credentials** across
  all PRD-scenario variants — a permanent, CI-gated invariant.

### CUJ-4 — stdio MCP server authenticates with no secret in env/config/context (S2 Priya / P5 Alex)

- **Trigger:** a local stdio MCP server needs to call an upstream API.
- **Path:** the server is launched **under the broker** with a reference/placeholder in its config instead
  of a real value → at tool-call time the broker resolves the reference, mints a scoped token, and injects
  it at egress → the upstream call succeeds → the server's config, environment, and the agent transcript
  never contained the secret.
- **Unhappy:** the server shares the *same readable runtime* as arbitrary agent code (the honest hard
  case) → documented: the broker requires a protected process boundary (sidecar/own user) and says so ·
  server ignores the reference and reads `os.environ` → the evasion event fires (CUJ-6).
- **Requirements:** R2, R7, R8, E7. **Acceptance:** an upstream authenticated call completes while a scan
  of config + env + transcript finds no secret; the pattern is documented for server authors and prepared
  for an **MCP ext-auth contribution** (PRD 20).

### CUJ-5 — Token binding proven: replay elsewhere fails (P2 Ravi)

- **Trigger:** Ravi tries to reuse an issued token against the wrong server, the wrong tool, or after the
  session ended.
- **Path:** each of the three bindings (audience RFC 8707, tool scope, session) is asserted by the broker
  and the egress injector → replay fails and is logged as `exchange-rejected`.
- **Unhappy:** a downstream ignores the audience claim → the broker's injection still scopes to one
  audience (defence in depth) and the event records that the target did not enforce it.
- **Requirements:** R3, E3. **Acceptance:** three binding-replay fixtures all fail closed and are logged.

### CUJ-6 — Secret-evasion caught (P1 Maya)

- **Trigger:** an agent (or a poisoned tool) tries to read a raw credential — `.env`, a cloud credential
  file, or the keychain — outside the broker.
- **Path:** in monitor-safe mode, the attempt is a **high-severity event**; in enforce mode it is blocked
  (via the composed enforcer: agentkernel/agentseatbelt) and the event records both.
- **Unhappy:** the read path is not covered by the available enforcer on this OS → agentkeys is honest: it
  records the attempt and names the gap; it never claims to have blocked what it could not.
- **Requirements:** R7, E10. **Acceptance:** the evasion pack is caught in monitor-safe mode; blocked-and-
  logged in enforce mode where an enforcer is composed.

### CUJ-7 — Step-up JIT issuance for a prod credential (P1 Maya → P2 Ravi)

- **Trigger:** an agent wants a production-class credential (e.g., a prod deploy token) that the session
  was not issued at start.
- **Path:** the broker requests a policy decision → agentpolicy returns `ask` → a human approves → the
  broker mints the **upgraded** token with a tighter TTL → the upgrade is recorded
  (`authorization.source=human`). No approval → no upgrade, no credential.
- **Unhappy:** the approver denies → the agent gets a structured deny it can rescope · the `ask` times out
  → deny (per agentpolicy's timeout=deny), no credential.
- **Requirements:** R9, E3, E9. **Acceptance:** a prod-scoped issuance cannot occur without an approving
  decision; the upgrade and its provenance are in the ledger.

### CUJ-8 — Backend fail-closed day (P1 Maya)

- **Trigger:** the keychain is locked / the backend is unreachable / the config is ambiguous.
- **Path:** issuance is **denied**; the agent gets a structured denial it can surface; `doctor` explains
  the effective backend and semantics; no static or env fallback occurs.
- **Unhappy:** a partial config that *could* be read as a fallback → refused loudly, never "best effort".
- **Requirements:** R5, E4, E9. **Acceptance:** the fail-closed fault matrix (locked/absent/ambiguous
  backend) is deny-or-pending on every path, never allow.

### CUJ-9 — Credential-lifecycle audit reconstruction (P3 Dana)

- **Trigger:** post-incident review of a session where an agent reached for prod.
- **Path:** `agentkeys export --session <id>` → ordered events: reference resolved, issuance (with
  audience/tool/session binding), use, step-up (if any), revoke, plus the agentwatch events and the hash
  chain → Dana verifies the chain and joins to the session trace by `session_id`.
- **Unhappy:** a rejected exchange → `exchange-rejected` with reason · a missing backend event → explicit
  gap marker, never silence.
- **Requirements:** R6, E12. **Acceptance:** a full credential lifecycle is reconstructable per session;
  the chain verifies; a scan finds no secret material in the export.

### CUJ-10 — Rotate a backend secret without restarting the agent (P1 Maya)

- **Trigger:** the underlying secret is rotated.
- **Path:** Maya updates the value in the backend → the next resolution uses the new value → the agent
  never restarts and never notices, because it holds a reference.
- **Unhappy:** old tokens minted before rotation → they expire on their short TTL (and can be revoked
  immediately if needed).
- **Requirements:** R1, R2, R4. **Acceptance:** post-rotation call succeeds with no agent restart; a
  pre-rotation token is dead within its TTL.

### CUJ-11 — Air-gapped / offline day (P1 Maya)

- **Trigger:** a regulated environment with no outbound network.
- **Path:** keychain/file backends only; local broker + local ledger; no external calls attempted; `doctor`
  confirms offline mode.
- **Unhappy:** config references a cloud backend not yet supported → `doctor` warns and refuses to silently
  drop; nothing is queued to a network that does not exist.
- **Requirements:** R5, E4, E12. **Acceptance:** CUJ-1/CUJ-2 pass with the network disabled.

### CUJ-12 — Two harnesses, one broker (P1 Maya)

- **Trigger:** Maya runs Claude Code and Cursor against the same tools.
- **Path:** the same broker serves both via their respective egress points (env virtualization / header
  rewrite) → the same reference, the same bindings, the same revoke.
- **Unhappy:** a harness with no usable interception point → documented lower-layer coverage or an honest
  "not yet", never a false "supported".
- **Requirements:** R2, E8, [PRD 19](19-harness-compatibility.md). **Acceptance:** ≥2 Tier-1 harnesses
  pass their recipe at v0.1.0; each recipe ends in a verified authenticated call.

### CUJ-13 — Embed the broker in a product (P5 Alex)

- **Trigger:** Alex's product needs a "security-review-ready" credential path.
- **Path:** the broker contract + CLI/SDK is embedded → his backend (his own vault) implements the pluggable
  interface → his agents hold references → his security reviewer sees bound, revocable, evidenced access.
- **Unhappy:** his backend cannot guarantee a required capability (e.g., no atomic single-use issuance) →
  it fails the conformance suite and is rejected **at load**, never at runtime.
- **Requirements:** E1, E9. **Acceptance:** a sample host app issues, uses, and revokes through the broker;
  a non-conforming backend is refused.

### CUJ-14 — Enterprise reviewer tries to buy it (P3 Dana) — scoping journey

- **Trigger:** Dana evaluates agentkeys for a 400-engineer org.
- **Path:** the docs state clearly: local-first v0.1.0; keychain/file backends only; no SSO/SCIM/multi-
  tenant/WORM; hash-chained ledger and export today; server mode, cloud backends, and identity are roadmap;
  the standards (RFC 8693/8707/9700, WIMSE/AIMS) are the interop shape.
- **Unhappy:** she needs SAML **today** → the honest answer is "not yet", with the gap table
  ([PRD 03 §4](03-landscape.md)) and the roadmap.
- **Requirements:** honesty clause ([PRD 20](20-standards-and-claims.md)). **Acceptance:** no unsupported
  enterprise claim anywhere in the docs; the gap list matches the roadmap.

## 4. Journey → requirement coverage

| CUJ | Personas | Requirements |
|---|---|---|
| CUJ-1 | Sam | R1, R2, R5, R17, E1, E7 |
| CUJ-2 | Jordan | R4, E3, E6 |
| CUJ-3 | Ravi | R1, R2, R7, E5 |
| CUJ-4 | Priya, Alex | R2, R7, R8, E7 |
| CUJ-5 | Ravi | R3, E3 |
| CUJ-6 | Maya | R7, E10 |
| CUJ-7 | Maya, Ravi | R9, E3, E9 |
| CUJ-8 | Maya | R5, E4, E9 |
| CUJ-9 | Dana | R6, E12 |
| CUJ-10 | Maya | R1, R2, R4 |
| CUJ-11 | Maya | R5, E4, E12 |
| CUJ-12 | Maya | R2, E8 |
| CUJ-13 | Alex | E1, E9 |
| CUJ-14 | Dana | honesty |

The full requirement → CUJ → WBS → test → scenario trace is [PRD 12](12-traceability.md) (next).

## 5. What we deliberately do **not** optimize for

- **A network-trust boundary**: egress injection must work locally and air-gapped, not only through a
  gateway.
- **A single harness's UX**: a broker that only works for one harness is not a broker.
- **Convenience over the invariant**: an "easy" path that puts a real secret back in the context is not a
  feature, it is the bug we exist to remove.
- **Enterprise completeness in v0.1.0**: pretending to have SSO/multi-tenancy would be worse than stating
  the gap ([PRD 03 §4](03-landscape.md)).
