# PRD 09 — Roadmap

**BLUF:** agentkeys ships in four steps, each with **one headline capability** and a hard **exit gate**
that is passed or not passed — no "mostly done". **v0.1.0** is the complete never-in-context local
lifecycle (R1–R9 + R17 + E1–E15), including the flagship stdio-MCP virtualization nobody else covers
and the scan/migrate tooling that makes adoption minutes. **v0.1.x** adds enterprise/cloud backends (R10),
the posture report (R18), and pays down field-test evidence. **v0.2.0** turns the
local broker into a server/HA/fleet broker with real workload identity (R11 + R12). **v0.3.0** adds the
product-depth slate (R13–R16), reaches **all five Tier-1 harnesses**, and lands the **MCP stdio-credential
ext-auth contribution**. The spine never regresses: kill-time ≤1s, zero usable secrets, fail-closed,
no token passthrough. Sequencing follows [PRD 05 §D](05-features.md) and is gated against
[PRD 08](08-risks.md).

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Sequencing principles

1. **One headline capability per release.** A release is remembered for one thing. Everything else in it
   is either a *correctness dependency* of that capability or *hardening* — never a second headline.
2. **Evidence gates the release, not a date.** Each gate is a pass/fail artifact: a conformance report, a
   fault matrix, a benchmark, a hand-maintained field-test verdict. A gate is not "mostly green".
3. **The spine is invariant across every release.** Kill-time ≤1s (R4, I3), zero usable secrets (R1, I1),
   fail-closed (E4, I2), no token passthrough (E14, I5), and unconditional revocation must **never**
   regress; a regression is a release blocker, not a roadmap item.
4. **Additive contracts only.** Token/issuance schemas and event names are extended, **never renumbered**
   (E11). A later release must be able to read an earlier release's references and store.
5. **Scope may only shrink.** A release that is running long loses scope; it does not slip its headline or
   absorb a new feature (see §8).
6. **Dependencies first.** Identity (R12) is a server-side concern, so it follows fleet mode (R11); the
   backend contract (E9) precedes the enterprise backends (R10); standards stay *aligned* until the
   release that *implements* them ([PRD 20 §2](20-standards-and-claims.md)).

## 2. Release map

| Release | Requirements | Headline capability | Exit gate (summary) |
|---|---|---|---|
| **v0.1.0** | **R1–R9 + R17 + E1–E15** | The complete **never-in-context credential lifecycle**, local-first, stdio-MCP flagship + scan/migrate | All P0 acceptance criteria green; conformance report green (E13); fail-closed fault matrix 100% deny-or-pending; kill-time CI ≤1s; context-dump finds 0 usable creds; scan 100% recall on seeded fixtures; ≥2 Tier-1 harness recipes verified; signed release + SBOM + Scorecard; **hand-maintained** field test |
| **v0.1.x** | **R10** + field-test hardening | **Enterprise / cloud backends** on the same `Backend` contract (1Password, Vault, K8s, AWS/GCP/Azure) | Every new backend passes the conformance suite; fail-closed on backend outage (E4); field-test misses triaged and closed; **no P0 regression** on the spine |
| **v0.2.0** | **R11 + R12** | **Server / HA / fleet broker** with **SPIFFE/WIMSE workload identity** | Cluster-safe store capability gated (E2); parent→child delegation proven **monotonically narrowing**; SPIFFE ID accepted as a WIMSE identifier (RFC 8693 `actor_token`); CIS-benchmarked deployment manifests |
| **v0.3.0** | **R13 + R14 + R15 + R16 + R19** + all-5 Tier-1 + MCP ext-auth **landed** | **Product depth**: blast-radius budgets, sender-constrained tokens, MCP attestation feed, egress taint/DLP, canary references | DPoP conformance (RFC 9449); budget exhaustion halts via agenthalt; signed attestation feed; taint denies secret/PII flow to external sinks; canary fires on first use with attribution; **all 5 Tier-1** recipes verified; **ext-auth contribution filed/landed** ([PRD 20 §3](20-standards-and-claims.md)) |

## 3. v0.1.0 — the never-in-context lifecycle (R1–R9 + R17, E1–E15)

**Headline:** an agent authenticates to a real system without ever holding the credential, and
`agentkeys revoke` kills it in ≤1s.

**In scope:** reference-only context (R1), egress injection across env/header/exchange (R2), bound tokens
(R3), one-command revoke (R4), keychain + file backends (R5), hash-chained lifecycle ledger (R6),
secret-evasion detection (R7), **stdio MCP virtualization** (R8, the flagship), step-up issuance (R9),
**secret-hygiene scan + guided migration** (R17 — the adoption unlock), and
the full engineering set — contract, durable store, single-use issuance, fail-closed, redaction, time
correctness, the injection engine, harness adapters (≥2 Tier-1), pluggable backends, outside-the-agent
control plane, versioning, ledger/export, the standards conformance gate, no passthrough, and supply-chain
integrity (E1–E15).

**Exit gate (all required):**

- [ ] Every P0 acceptance criterion in [PRD 05 §A/§B](05-features.md) passes its test.
- [ ] Standards **conformance report is green** on the release commit (E13, [PRD 20 §1](20-standards-and-claims.md)).
- [ ] **Fail-closed fault matrix** is 100% deny-or-pending — never allow, never silent (E4).
- [ ] **Kill-time harness ≤1s**, end-to-end (issue → revoke → replay fails), running **in CI** (R4).
- [ ] **Context-dump pack finds 0 usable credentials** across every variant (R1).
- [ ] **≥2 Tier-1 harness** recipes end in a verified authenticated call (E8).
- [ ] **Scan/migrate** (R17): 100% recall on the seeded fixture, 0 printed secret values; migrate moves a
      secret end-to-end and closes the finding (SC-51).
- [ ] **Signed release + SLSA provenance + SBOM + OpenSSF Scorecard target**; `security.txt` live (E15).
- [ ] Reproducible benchmark (`bench/`) published; **hand-maintained field-test report** entered by hand.

## 4. v0.1.x — enterprise backends, posture + field-test hardening (R10 + R18)

**Headline:** the same broker, the backends an enterprise already runs — with the residual risk visible.

**In scope:** R10 — 1Password, HashiCorp Vault, Kubernetes Secrets, and AWS/GCP/Azure secret managers —
behind the **same conformance-gated `Backend` contract** (E9); R18 — the `agentkeys posture` report
(env-resident secrets, unbrokered servers, TTL drift, revoke counts); plus hardening driven by
field-test misses.

**Why here:** the backend contract (E9) already ships at v0.1.0; R10 is new *drivers* admitted only by
passing the conformance suite. This keeps enterprise reach additive and avoids a rewrite — and it keeps the
v0.1.0 promise (keychain + file, fail-closed) intact while the enterprise list grows.

**Exit gate:**

- [ ] Each new backend passes `agentkeys conformance`; a failing backend is **rejected at load** (E9).
- [ ] A backend outage still fails closed and stays legible via `doctor` (R5, E4).
- [ ] Every field-test miss from v0.1.0 is either closed or **explicitly published as a residual** ([PRD 08](08-risks.md)).
- [ ] `agentkeys posture` enumerates every finding class on the fixture machine with **0 secret material** (R18, SC-52).
- [ ] **No P0 regression**: the v0.1.0 spine gates are re-run and green on the v0.1.x commit.

## 5. v0.2.0 — server / HA / fleet + workload identity (R11, R12)

**Headline:** many agents, one broker — with real workload identity.

**In scope:** R11 — a central broker for many agents, with parent→child delegation and **monotonic
narrowing** (a child can never hold more than its parent); R12 — SPIFFE/WIMSE workload identity: SVIDs
(JWT/X.509/WIT) as the actor credential, joined to `gen_ai.agent.id`, carried as the RFC 8693
`actor_token`.

**Why here:** R11 must land before R12, because workload identity is meaningful once the broker serves
workloads, not a single local session. The store grows its **cluster-safe** capability flags (E2), and
delegation reuses the same issuance/binding core — additive, not a fork.

**Exit gate:**

- [ ] The store driver declares and enforces cluster-safe capabilities; configs it cannot guarantee are
      **refused at load** (E2).
- [ ] Parent→child delegation is proven **monotonically narrowing** in the conformance suite.
- [ ] A SPIFFE ID is accepted as a WIMSE identifier and the conformance report is green ([PRD 20 §2](20-standards-and-claims.md)).
- [ ] Transaction-token propagation is tracked (aligned), not claimed.
- [ ] CIS-benchmarked hardened deployment manifests published.
- [ ] Spine gates re-run green; **no P0 regression**.

## 6. v0.3.0 — product depth, all harnesses, standards authorship (R13–R16)

**Headline:** the product is deep enough to be the default — and the stdio pattern is owned upstream.

**In scope:** R13 blast-radius budgets (cumulative caps, exhaustion auto-halts via agenthalt), R14 DPoP
sender-constrained tokens (RFC 9449), R15 MCP-server attestation/reputation feed, R16 egress taint/DLP,
R19 canary references (broker-native honeytokens; auto-revoke composition owned by agenthalt).
Plus: **all five Tier-1 harnesses** (E8 milestone), and the **MCP stdio-credential ext-auth contribution
landed** ([PRD 20 §3](20-standards-and-claims.md)) — owning the default for the vector we opened.

**Exit gate:**

- [ ] DPoP passes RFC 9449 conformance; a stolen token string alone is insufficient (R14).
- [ ] Budget exhaustion auto-halts through agenthalt; a widened budget requires an explicit grant (R13).
- [ ] The attestation feed is signed and consumable; poisoned/rug-pulled tools can be flagged (R15).
- [ ] Taint/DLP denies secret/PII-bearing tool output from flowing to external sinks (R16).
- [ ] A **canary reference** fires on its first use attempt with full attribution (R19, SC-53); the
      auto-revoke decision is agenthalt's, recorded as such.
- [ ] **All 5 Tier-1 harness** recipes verified end-to-end (E8).
- [ ] The **MCP ext-auth contribution** is filed (and, where accepted, landed); the pattern in code and
      the pattern proposed are the same pattern.
- [ ] Spine gates re-run green; **no P0 regression**.

## 7. Why "one headline capability per release"

- **It keeps the spine trustworthy.** If a release has two equal headlines, one of them gets less proof.
  A single headline means the release's exit gate is unambiguous: did the one thing ship, and is it
  proven?
- **It makes "no" cheap.** Saying no to a feature is easy when the release's identity is one capability;
  it is painful when everything is a headliner.
- **It matches the buyer's question.** Each release answers exactly one question — v0.1.0 "does it keep
  the secret out and kill it in a second?", v0.1.x "does it work with my backends?", v0.2.0 "does it scale
  to my fleet and my identity?", v0.3.0 "is it deep and standard enough to be the default?".
- **It preserves additive contracts.** One capability per release keeps schema/event changes small and
  reviewable, so E11 compatibility holds release over release.

## 8. The anti-scope rule

> **A requirement may not move to an earlier release unless it is (a) required for that release's headline
> capability to be *correct*, or (b) a security / fail-closed correctness fix. Anything else waits its
> turn. No release absorbs "while we're here" features.**

- **Growth always enters at the end of the line.** A new idea becomes a new P2 requirement (or a new
  requirement ID) scheduled at the tail — it is **never inserted mid-ladder** and never renumbers an
  existing ID.
- **Scope may only shrink.** When a release is at risk, the correct move is to cut scope to protect the
  headline and its gate — not to extend the release or weaken the gate.
- **The exception is narrow and audit-able.** A security/fail-closed fix may jump forward; it must cite
  the invariant it protects (I2, I3, I5) in the change. "It would be nice in this release" does not.
- **Why this is a rule and not a preference:** a broker whose releases absorb extras stops being provable.
  The evidence strategy ([PRD 07](07-success-metrics.md)) only works if the scope of each release is small
  enough to actually gate.

## 9. What does **not** move (stability commitments)

| Commitment | Holds across |
|---|---|
| Kill-time ≤1s, end-to-end | v0.1.0 → v0.3.0 (never regresses) |
| Zero usable secrets from a context dump | v0.1.0 → v0.3.0 |
| Fail-closed on backend/store/sink failure | v0.1.0 → v0.3.0 |
| No token passthrough; audience enforced at egress | v0.1.0 → v0.3.0 |
| Revocation is unconditional, never policy-gated | v0.1.0 → v0.3.0 |
| Additive-only schemas/events (no renumber) | v0.1.0 → v0.3.0 |
| Local-first, air-gapped operation | v0.1.0 → v0.3.0 (server mode is additive) |

## 10. How gates compose

Each release's gate is the previous release's gate **plus** its new headline — never instead of it. Before
a release ships, the earlier spine gates are re-run on the new commit, so "no P0 regression" is checked,
not assumed. This is the same posture as the hand-maintained field-test report: verdicts are entered from
committed evidence, by hand, and a miss is published rather than smoothed. See
[PRD 12](12-traceability.md) for requirement → release → test traceability and
[PRD 21](21-evidence-register-and-method.md) for the evidence register.
