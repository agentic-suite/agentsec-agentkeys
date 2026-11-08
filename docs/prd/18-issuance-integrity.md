# PRD 18 — Issuance Integrity

**BLUF:** The issuance is the moment agentkeys either holds its invariant or fails it — the second a
credential exists, *who asked for it, what it may touch, who approved it, and how it can die* must all be
answers, not assumptions. This document defines the **identity chain** (five identities, one line of
custody), the **issuance request pipeline** (every check, in order, each fail-closed), the **replay and
spoofing defenses** beyond the bindings, **step-up provenance** (what an approval actually proves), the
**revoke-vs-in-flight semantics** that make ≤1s honest, and the **multi-agent/shared-session rules**
(D-17). The tests that gate all of it are referenced, not redefined ([PRD 17](17-scenarios.md)).

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. What "integrity" means here

An issuance is a **grant of real capability**. Its integrity is the conjunction of five properties, each of
which is independently testable:

| # | Property | One-line test |
|---|---|---|
| P1 | **Attribution** — every issuance names a principal, a session, a reference, and a binding | The ledger row has all four |
| P2 | **Minimality** — no issuance is broader than its binding allows | Widening attempts are refused (SC-42) |
| P3 | **Provenance** — a higher-class mint carries the decision (and approver) that authorized it | `provenance` on prod-class rows |
| P4 | **Unforgeability** — issuance secrets are single-use, hashed at rest, and bound to their context | Replay/forward/stale fixtures all fail (SC-11) |
| P5 | **Mortality** — every issuance dies by TTL, use, session end, or revoke — and the revoke lands ≤1s | Kill-time benchmark (SC-24) |

## 2. The identity chain (five identities, one custody line)

This is the model every other document assumes. Each identity is **asserted by exactly one party** and
**authorizes exactly one thing** — conflating them is the classic confused-deputy bug.

| Identity | What it is | Who asserts it | What it authorizes | Where it appears |
|---|---|---|---|---|
| **Reference identity** | The opaque handle to a backend slot (`akref:…`) | The broker, at registration | *Which secret may be resolved* — nothing about who or where | Agent context, configs, `reference_id` |
| **Agent/session identity** | The agent + session a binding belongs to | The broker, at session start (B1 channel) | *Whose activity this is* — the attribution spine | `agent_id`, `session_id` on every event |
| **Subject** (the human) | The person on whose behalf the agent acts | agentpolicy / the approval flow (never the agent) | *Delegated authority* — the right to ask at all | `provenance.decided_by`, `authorization.source` |
| **Actor** (the workload) | The machine identity of the agent process | At v0.1.0: the OS principal of the broker channel; at **R12**: a SPIFFE/WIMSE SVID | *Proof the requester is the workload it claims* — carried as the RFC 8693 `actor_token` | `act` claim in exchanged tokens |
| **Execution credential** | The short-lived token minted for one call | The broker, at egress | *One audience, one tool, one session, one use* | The injected header/env/exchange value — never stored |

**Custody line:** subject authorizes → agent/session requests → actor is proven → reference resolves →
execution credential is minted → it dies. Every hop is an event; no hop trusts a claim it did not verify.
(Workload identity at R12 strengthens the **actor** link; it does not change the shape.)

## 3. The issuance request pipeline (every check, in order)

A resolution request arrives at the broker over the local OS-authenticated channel (B1,
[PRD 02 §3](02-architecture.md)). The checks are **ordered and short-circuiting** — the first failure
denies with a reason, and no later check runs:

| # | Check | Question | Failure → |
|---|---|---|---|
| 1 | **Channel authN** | Is the caller a local principal the broker accepts? | `exchange-rejected` (unknown principal) |
| 2 | **Session validity** | Is the session live, unrevoked, and bound to this agent? | Reject; revoked sessions refuse (epoch check, §5) |
| 3 | **Reference validity** | Does the reference exist, belong to an enabled backend, and match the request's binding shape? | Reject with a diagnostic naming the field |
| 4 | **Binding authorization** | Is `(reference, audience, tool)` in the allowed bindings for this session? | Reject; **the binding is the ceiling** (E7) |
| 5 | **Class gate / step-up** | Does this class require a decision? If yes: was one granted, and is it fresh? | No approval or timeout → **deny** (R9; timeout = deny) |
| 6 | **Mint** | Generate the 128-bit single-use secret; store **hashed**; bind `(reference, audience, tool, session)`; set TTL within class floor/ceiling | — |
| 7 | **Inject** | A driver applies the credential at egress; audience enforced even if downstream won't | Wrong audience → refuse to inject (E14) |
| 8 | **Record** | Ledger row + agentwatch event; redaction receipts for any shaped field | — |

**Idempotency:** a retry of the same `(reference, binding)` within the window returns the **same issuance**
and re-injects nothing new (E1). **Exactly-once:** at most one live issuance per binding per window
([PRD 15 §6](15-data-model.md)).

## 4. Replay and spoofing defenses (beyond the bindings)

The bindings (R3) are the primary defense — wrong-audience/wrong-tool/post-session replays all fail
(SC-08…SC-10). This section covers what the bindings *don't*:

| Attack | Defense | Test |
|---|---|---|
| **Forged reference** (agent invents `akref:…`) | References are registered, not guessed; an unknown reference is a rejection with the shape named — and **reference enumeration is detectable** (repeated unknown-reference probes are an `evasion-detected`-class signal) | `tests/test_reference_grammar.py` + SC-41 |
| **Replayed request** (same request, twice) | Idempotent keyed by reference+binding: the second request returns the same issuance — it never mints twice | `tests/test_idempotency.py` |
| **Stolen session credential** (the agent's own channel secret leaks) | It yields **bounded tokens only** — per-call, per-audience, minutes-scale — and dies at revoke/session end; there is no vault behind it to drain (D-01) | Kill-time + binding fixtures |
| **Scope widening** (agent asks for a wider audience than the binding) | The binding is the ceiling; the injector cannot widen (E7); attempts logged (SC-42) | `tests/test_inject_*` fixtures |
| **Downstream ignoring the audience** | We enforce the audience **at egress** regardless (E14) and record that the target did not check — defence in depth, honestly | `tests/conformance/test_rfc8707.py` |
| **Killed-broker replay** (broker down; agent replays a minted token) | Issued tokens stop authenticating with session state (store is the truth, not broker liveness); TTL is the backstop | SC-26-adjacent fault fixtures |
| **Two agents, one session** (identity confusion) | A session binds exactly one agent (D-17); the second agent's requests are rejected, logged | §6 rules + `tests/test_binding_session.py` |

## 5. Step-up provenance — what an approval actually proves

When a class requires a decision (R9), the mint records **what was decided, by whom, on what basis**:

- `provenance.decided_by` — the decision source (agentpolicy), never a free-text string from the agent.
- `authorization.source` — the human provenance class (e.g., `human-once`), per the agentwatch schema — the
  same vocabulary agentinbox produces, so the approval chain joins end-to-end.
- **Freshness** — an approval is bound to the request it answered; it is not a standing grant. A new
  request for the same class asks again (the "standing approval" convenience is deliberately *not* ours —
  it is agentpolicy's to model, [PRD 14](14-non-goals.md)).
- **Denials are first-class** — `step-up-denied` carries the reason and is visible to the agent as a
  structured deny it can rescope (CUJ-7).

**Timeout = deny.** No approval inside the window is a deny, never a default-allow (E4).

## 6. Multi-agent / shared-session semantics (D-17, frozen)

The ecosystem PRD left "multiple agents, one user credential — inherit, split, or deny?" open. The frozen
answer:

1. **One session, one agent.** A session binds exactly one agent identity; attribution is never shared.
2. **No ambient inheritance.** Two agents may reference the same backend secret, but only via **separate
   references, sessions, bindings, and revocation domains** — sharing the *secret* never shares the
   *authority*.
3. **Delegation (R11) is explicit and monotonically narrowing** — a child's audience/tool/class can never
   exceed its parent's; the chain is recorded in the custody line.
4. **Revoke domains are separate** — killing a child never kills the parent; killing the parent
   **cascades** to children (that asymmetry is the point: authority flows down, kill flows down, blame
   never flows up silently).

## 7. Revocation semantics (why ≤1s is honest)

- **Epoch, not enumeration.** Revoke is a **CAS on the session's `revoke_epoch`** ([PRD 15
  §6](15-data-model.md)) — one atomic store write, not a walk of issued tokens. Every subsequent
  resolution and every live token check consults the epoch; that is why the kill is O(1) and provable.
- **In-flight calls** — a call already injected completes its hop, but the **next hop fails**: the
  single-use consumption plus epoch check guarantees no second use (SC-26).
- **Revoke vs. TTL** — TTL is defence in depth; revoke is the operator's act. Neither gates the other:
  revocation is never policy-gated (D-07), and TTL expiry never *replaces* revocation in evidence.
- **Unknown target** — revoking a nonexistent agent/session is a loud error, never a silent no-op (SC-27).
- **The `revoked` event** carries scope, target, operator principal, and `effective_at` measured against
  the ≤1s budget (SC-28).

## 8. What gates this document

Every property here maps to an existing fixture or scenario: binding replays (SC-08…SC-11), idempotency
and exactly-once (SC-23), tamper-against-us (SC-41), scope widening (SC-42), step-up (SC-33/SC-34),
kill-time (SC-24…SC-28), single-use (E3 fixtures), and the conformance suite for the RFC shapes (E13).
Integrity is **tested per release**, not asserted per slide — the trace is
[PRD 12](12-traceability.md).

## 9. Related documents

- The boundaries the pipeline lives inside: [PRD 02 — Architecture](02-architecture.md).
- The entities and contracts it manipulates: [PRD 15 — Data Model](15-data-model.md).
- The frozen decisions behind D-17 and the epoch model: [PRD 11 — Decisions](11-decisions.md).
- The threat model these defenses answer: [PRD 06 — Security Baseline](06-security-baseline.md).
