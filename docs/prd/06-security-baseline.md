# PRD 06 — Security Baseline

**BLUF:** agentkeys holds the credentials for everything an agent can reach, which makes it the
highest-value target in the stack. This document is the honest security baseline: the **invariants** that
must never regress, the **STRIDE** analysis of the broker itself, our **own threat model** ("we are a
target" — Plugin4Shell proved attackers go after the agent tooling), and the **non-claims** we refuse to
make. The posture is one sentence: *fail closed, keep the secret out of the agent's world, keep the broker
outside the agent's control plane, and prove it in CI.*

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Invariants (a regression is a release blocker)

| # | Invariant | Enforced by | Tested by |
|---|---|---|---|
| **I1** | **Never-in-context** — no real secret is ever rendered into agent context, arguments, generated code, or logs | reference model (R1), redaction (E5) | context-dump pack (R1) |
| **I2** | **Fail closed** — no path from a failure (backend down, store corrupt, config ambiguous, sink offline) to a credential | R5, E4 | fault-injection matrix |
| **I3** | **Revocation is unconditional** — `revoke` is never gated on policy and never depends on TTL expiry | R4 | kill-time CI |
| **I4** | **Single-use, bound issuance** — an issuance is bound to `(reference, audience, tool, session)` and cannot be replayed, forwarded, or widened | R3, E3 | binding-replay fixtures |
| **I5** | **No token passthrough** — the broker never forwards a client token upstream; it mints a scoped credential | E14 | passthrough fixture |
| **I6** | **Outside the agent's control plane** — the broker is a separate process the agent cannot read, edit, or silently kill | E10 | tamper fixtures |
| **I7** | **Redaction before persistence** — secret-shaped material is masked before storage/render/export, with receipts | E5 | evidence scanner |
| **I8** | **Tamper-evident record** — the lifecycle ledger is hash-chained; tampering is detected, never silently accepted | R6, E12 | chain verification |
| **I9** | **Time cannot be gamed** — a clock jump cannot extend a TTL or resurrect an expired issuance | E6 | clock-skew fixtures |
| **I10** | **Supply chain is clean** — signed releases, provenance, SBOM, pinned deps | E15 | Scorecard/attestations |

## 2. STRIDE analysis of the broker

| Threat | Surface | Scenario | Mitigation |
|---|---|---|---|
| **Spoofing** | Egress injector / issuance API | A rogue local process asks the broker to resolve a reference it should not | Local, OS-authenticated control channel (unix socket, file perms); per-principal broker auth; issuance bound to agent/session identity |
| **Tampering** | Config, backend adapters, ledger | Attacker edits broker config to always-allow, or rewrites the ledger | Config integrity checked at start → **fail closed + loud event** (E10); hash-chained ledger (I8); policy changes are signed/reviewed |
| **Repudiation** | Lifecycle record | "Who revoked the agent?" is unanswerable | Every event is attributed (principal + channel + timestamp); operator identity on `revoked` |
| **Information disclosure** | Broker memory / logs / export | The broker leaks the very secret it protects | Secrets held only transiently (keychain unlocked per-exchange); never logged (E5); redaction receipts; export is secret-free by scan |
| **Denial of service** | Issuance hot path | An agent floods the broker to exhaust it or force an unsafe default | Bounded work per exchange; fail closed under load (never fail open); rate limit per agent; agenthalt composition |
| **Elevation of privilege** | Reference resolution / step-up | An agent with a low-class reference tries to obtain a prod-class credential | Class-scoped backends + step-up approval (R9); monotonic narrowing (never widen); revocation cascade |

## 3. Our own threat model — "we are a target"

> A broker that holds every credential, trusted by every harness, is the single best thing for an attacker
> to compromise. If our product falls, the attacker owns every agent it guards. We design for that.

| Surface | Threat | Mitigation |
|---|---|---|
| **Broker process** (holds creds) | Compromise → steal every downstream secret | Secrets in OS keychain / HSM-backed backends, never plaintext on disk; broker isolated (own user/container); short-lived in-memory tokens only; unlock-per-exchange so compromise ≠ bulk theft |
| **Reference grammar / parsers** | Crafted reference or frame → code execution / crash → DoS on enforcement | Strict grammar; OSS-Fuzz; size/complexity limits; crash-safe fail-closed |
| **Egress injectors** | Injection of an attacker-chosen audience/scope; smuggling | Audience/scope fixed by the binding, not the agent; no widening (E7); fixture-tested |
| **Backend adapters** | A malicious/compromised backend answers with the wrong secret or exfiltrates references | Backends are conformance-gated (E9), capability-flagged, and never trusted to widen scope |
| **Ledger / telemetry** | Stored-XSS/injection via crafted reference or tool names into our own logs/UI | Treat all telemetry as untrusted input; escape/encode; no dynamic rendering of agent-controlled strings |
| **Supply chain (our deps)** | A compromised dependency makes us the malware on every machine | E15: SLSA/Sigstore/SBOM/pinned deps/Scorecard A; the Plugin4Shell lesson |
| **Update channel** | Auto-update re-runs a malicious payload (Plugin4Shell) | No silent background code execution; signed, pinned update channel; update verification is itself a decision |
| **Hook/config surface** | Attacker disables enforcement by editing our config | Integrity check at session start; tamper → fail closed + alert; lockable config |
| **The agent itself** (our subject) | Agent is told to "ignore security tooling", disable the broker, or read secrets | Enforcement lives **below** the agent: broker outside its context, egress below its code, secrets in a process it cannot read; **evasion is a detected event** |

### Core anti-tamper principles

1. **Enforcement must live outside the agent's control plane** — anything the agent can edit or kill is
   advisory, not enforcement.
2. **Fail closed on tamper** — integrity-check failure blocks; it does not warn-and-continue.
3. **Assume the harness is compromised** — a hijacked Claude Code/Cursor process still must not extract
   brokered credentials or edit the broker.
4. **Separation of duties** — the thing that *holds* secrets (broker/backends) ≠ the thing that *decides*
   (agentpolicy) ≠ the thing that *enforces* (agentkernel/agentseatbelt) ≠ the thing that *observes*
   (agentwatch). Compromising one must not compromise all.

## 4. The stdio boundary (the honest hard case)

A stdio MCP server is a **child process**. If it shares the same readable runtime as arbitrary agent code
(co-located subprocess, same user, same env domain), it can be made to read anything that runtime can read.
agentkeys addresses this by **moving the credential across a process boundary**: the server runs under the
broker's protection (own user/sidecar/container) and receives credentials at egress, not in its env. Where
that boundary cannot be established, agentkeys **says so** and records the attempt — it never claims a
guarantee it cannot hold. This limit is a first-class, documented property, not a footnote.

## 5. Privacy — what we store, and what we never store

| Stored | Never stored |
|---|---|
| References (opaque handles) | Secret material of any kind |
| Bindings (`audience`, `tool`, `session_id`) | Raw tool arguments that contain secrets (redacted with receipts) |
| Timestamps, TTLs, class | Full customer records / PII (redaction-by-default, E5) |
| Lifecycle events (issuance/use/upgrade/revoke/reject/evade) | Credential values in logs, exports, or events |
| Principal/operator identity for actions | Browser/session credentials (permanent refusal) |

## 6. Non-claims

- We do **not** claim to stop prompt injection; we make injection **not worth it** (nothing usable to steal).
- We do **not** claim absolute protection for a co-located, same-runtime stdio process (§4).
- We do **not** claim compliance certifications; we map to frameworks ([PRD 20](20-standards-and-claims.md)).
- We do **not** claim to detect every credential read; we flag the paths we cover and name the gaps.

## 7. Dogfooding / self-test

The shipped attack packs include attacks **against agentkeys itself**: reference spoofing, config tamper,
ledger rewrite, injector scope-widening, and evasion ("disable the broker"). These run in CI as regression
tests, so the product's own threat model is continuously exercised — not asserted once in a document.
