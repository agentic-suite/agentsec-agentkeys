# PRD 08 — Risks

**BLUF:** A credential broker is a security product that is also the **single best target in the stack**,
sold into a market where the incumbents are already "good enough" for the enterprise and where the
default developer behaviour — paste a long-lived key into `.env` — is the status quo we have to beat on
**ergonomics**, not just on security. This document is the honest risk register: the risks we accept and
watch with a **tripwire**, the ones we think about most, and the ones we have **deliberately dismissed**
and why. Every mitigation maps to a requirement in [PRD 05](05-features.md) or an invariant in
[PRD 06](06-security-baseline.md); nothing here is a promise we cannot trace to a control.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. How to read this register

- **Type** — *security* (we get breached / abused), *technical* (we cannot hold a property),
  *product* (we build the wrong thing), *adoption* (nobody uses it), *dependency* (something we rely on
  moves), *ecosystem* (a bigger player absorbs or invalidates us).
- **Likelihood / Impact** — *Low / Medium / High* likelihood; *Medium / High / Critical* impact. These are
  judgements, not measurements, and they are revisited each release.
- **Mitigation** — the control that reduces likelihood or impact, traced to a requirement.
- **Tripwire** — the **observable signal** that fires the risk so we act *before* it lands. A risk with no
  tripwire is a risk we are not actually managing. This mirrors the coverage-map posture in
  [PRD 03](03-landscape.md): name the gap, watch it, do not paper over it.

| Scale | Likelihood | Impact |
|---|---|---|
| **High** | Expected within the next release or two, or already observed | Blocks v0.1.0 / breaks an invariant / loses the product |
| **Medium** | Plausible within the year; depends on outside actors | Serious regression, recoverable with effort |
| **Low** | Unlikely but coherent; worth a tripwire | Local, bounded, contained by an existing control |

**Treatments.** Each risk is *mitigated* (a control reduces it), *accepted* (we watch it with a tripwire
and live with the residual), *avoided* (we design it out of scope), or *transferred* (a backend/IdP owns
it). The register is almost entirely **mitigate + accept-with-tripwire**; the *avoid* decisions live in
[PRD 14](14-non-goals.md), and *transfer* is wherever we consume a standard instead of reimplementing it.

## 2. Risk register

| # | Risk | Type | Likelihood | Impact | Mitigation | Tripwire |
|---|---|---|---|---|---|---|
| **R-1** | **Broker compromise — we are a target.** An attacker who owns the broker owns every credential it guards. | security | Medium | Critical | Secrets stay in keychain/HSM-backed backends, never plaintext on disk; broker isolated (own user/container); transient in-memory tokens; unlock-per-exchange so compromise is not bulk theft; STRIDE + "we are a target" model ([PRD 06 §2–3](06-security-baseline.md)); self-attack packs run in CI (spoof ref, tamper config, rewrite ledger, widen scope, "disable the broker") | Any self-attack pack that passes (a missed tamper); any CVE in the broker; any report of a stolen token being accepted |
| **R-2** | **stdio co-located-runtime hard case.** A stdio MCP server sharing the agent's readable runtime cannot be fully protected — the boundary may not exist. | technical | High | High | Move the credential across a process boundary (own user/sidecar/container) and require it ([PRD 06 §4](06-security-baseline.md)); where it cannot be established, **say so and record the attempt** — never claim a guarantee we cannot hold (R8 honest limit) | A stdio recipe that cannot establish a private runtime on a Tier-1 harness; a stdio secret found usable in a context dump |
| **R-3** | **Backend outage denies the agent.** Fail-closed is correct for security but turning "backend down" into "agent cannot work" is a denial-of-service on the user. | technical | Medium | High | Fail closed but degrade *usefully*: `doctor` explains the effective backend; ceremony caching where safe; per-class TTL floor/ceiling (E4, E6); never fall back to a static secret (R5). Outage = no **new** issuance, not a broken install | Sustained issuance-deny rate above baseline in field telemetry; an incident where a backend outage blocked a team for >1 working session |
| **R-4** | **MCP spec step-change breaks the stdio pattern.** A future MCP revision or ext-auth decision invalidates our stdio-virtualization approach. | dependency | Medium | High | Design the stdio pattern as a **contribution we intend to own upstream**, not a private hack ([PRD 20 §3](20-standards-and-claims.md)); implement to the spec as written and keep the injection layer transport-agnostic (E7) so a spec shift is an adapter change, not a rewrite | A draft MCP revision that changes stdio credential guidance; our ext-auth contribution being rejected or superseded |
| **R-5** | **Enterprise incumbents are "good enough."** Aembit / Entra Agent ID / 1Password already ship JIT creds and revocation; buyers see no gap to fund. | product / adoption | High | High | Do not fight on enterprise turf — own the **free, local-first, below-the-harness, stdio-inclusive** layer and interoperate with their backends/IdP ([PRD 03 §3](03-landscape.md)); compete on five-minute install (CUJ-1), not on control-plane features | Enterprise buyer feedback that "our vendor already covers this"; our install→first-call time failing the <15 min target |
| **R-6** | **A platform absorbs the idea.** LiteLLM / Snyk agent-scan / Cloudflare AI Gateway ship egress credential injection as a feature of their gateway or scanner. | ecosystem | Medium | High | Operate **below the harness and off the network path** so a gateway cannot reach the local stdio case ([PRD 01](01-why.md)); the moat is the invariant + reproducible evidence + stdio coverage, not the header-injection trick | A major gateway/scanner shipping stdio credential virtualization or a public ≤1s revocation benchmark before us |
| **R-7** | **Adoption friction — developers keep pasting keys.** Even a correct broker loses if the status quo is faster; teams leave raw keys in `.env`. | adoption | High | High | Make the brokered path **easier than the status quo**: one CLI, no cloud account, no agent-code change, `.env`-to-reference migration helper (F1), harness recipes for ≥2 Tier-1 (E8); measure the migration funnel ([PRD 07 §2.3](07-success-metrics.md)) | Field-test teams keeping a `.env` fallback; onboarding drop-off before the first brokered call |
| **R-8** | **Standards / skill drift.** WIMSE/AIMS, SPIFFE, transaction tokens, or ID-JAG move faster than our alignment; we build to a stale shape. | dependency | Medium | Medium | Track the drafts explicitly as **aligned, not implemented** ([PRD 20 §2](20-standards-and-claims.md)); consume standards (OAuth, SPIFFE, Cedar) rather than reimplement; keep R12 (WIMSE/SPIFFE) scheduled, labeled, and revisitable | A draft we align to being withdrawn or renamed; a conformance suite we implement to diverging from the shipped draft |
| **R-9** | **Supply-chain compromise.** A compromised dependency, build, or update channel makes us the malware on every machine — exactly Plugin4Shell's lesson. | security | Medium | Critical | E15: signed releases (Sigstore), SLSA provenance, pinned deps, SBOM, OpenSSF Scorecard A, OSS-Fuzz on parsers, `security.txt` + CVE program; no silent background code execution; update verification is itself a decision ([PRD 06 §3](06-security-baseline.md)) | Scorecard regression below target; unsigned/unattested artifact; a dependency advisory we cannot patch same-day |
| **R-10** | **Over-claiming destroys trust.** A single overstated guarantee ("we stop prompt injection", "absolute stdio protection") collapses the credibility the whole evidence strategy rests on. | product | Medium | High | Claims vocabulary with a **label never above its evidence** ([PRD 20 §6](20-standards-and-claims.md)); explicit non-claims ([PRD 06 §6](06-security-baseline.md)); the stdio boundary and coverage gaps are first-class, not footnotes | Any doc/marketing claim that outruns the field-test report; a claim that fails third-party reproduction |
| **R-11** | **Store/ledger corruption blocks issuance — or silently diverges.** Fail-closed store failure is safe but can become an outage; a diverged chain is a security event. | technical | Low | Medium | Single-writer, capability-gated BrokerStore (E2); kill -9 mid-issue recovery tested; `verify-log` treats any non-verify as a security event ([PRD 07 §5](07-success-metrics.md)); export is read-only | Corrupt-store fault matrix cell that does not fail closed; any session whose chain fails verification |
| **R-12** | **Single-maintainer / bus factor.** A small OSS broker with no second maintainer is one illness away from unmaintained, which enterprise buyers read as dead-on-arrival. | ecosystem / product | Medium | Medium | The reliability ladder is a **buyer requirement, not cleanup** ([PRD 20 §5](20-standards-and-claims.md)): signed releases, SBOM, Scorecard, CVE program all ship at v0.1.0; document bus factor honestly and recruit a second maintainer before claiming enterprise-readiness | A release with no independent reviewer; a security advisory with no on-call responder |

## 3. The risks we think about most

### R-1 — Broker compromise (security)

The broker is trusted by every harness and holds every credential; if it falls, so does everything it
guards. We accept this because the alternative — secrets in agent-readable configs — is strictly worse,
but we design *for* compromise: secrets are transient and backend-held, the broker is outside the agent's
control plane (E10), and its own threat model is exercised **in CI**, not asserted once. The tripwire is
deliberately adversarial: a self-attack pack that **passes** is worse than one that fails.

### R-2 — The stdio co-located runtime (technical)

This is the flagship's honest hard case ([PRD 05 R8](05-features.md)). We do not pretend a same-runtime
subprocess is protectable. Either the credential crosses a real process boundary, or we record the
attempt and name the gap. If a Tier-1 harness cannot provide that boundary, that is a **coverage miss we
publish**, not something we quietly reframe as covered.

### R-3 — Fail-closed must not become fail-useless (technical)

"Fail closed" is a security invariant, not a licence to break the user's afternoon. The failure we are
designing against is subtle: a locked keychain or a downed backend correctly denies **new** issuance, and
a naive implementation turns that into a dead agent with no explanation. The mitigation is to fail closed
*and* be legible — `doctor` names the effective backend, issuance pauses rather than corrupts, and no path
degrades to a static secret (R5, E4). We accept some availability loss; we refuse silent or fallback
behaviour.

### R-4 — A spec step-change (dependency)

The stdio credential pattern is the part of our design most exposed to an external decision. We treat it
as a **contribution we intend to own upstream** ([PRD 20 §3](20-standards-and-claims.md)), implement to the
spec as written, and keep the injection layer transport-agnostic (E7) so a spec shift is an adapter change,
not a rewrite. If MCP standardizes stdio credentials *without* us, we still benefit — the default becomes
safer — and our differentiator falls back to the invariant, the evidence, and the cross-harness broker.

### R-7 + R-5 — Adoption is the real existential risk

Security products die of non-use more often than of breaches. The incumbents are "good enough" for the
enterprise and the default behaviour is "paste the key"; our only durable edge is that the brokered path
is **faster and freer** than the status quo *and* covers the local stdio case nobody else does. If
install→first-call slips past 15 minutes, the security argument never gets heard.

### R-9 + R-10 — Trust is the product

For a security tool, provenance and honesty **are** the marketing. A supply-chain compromise (R-9) or an
overstated claim (R-10) is more damaging than a missing feature, because both convert our strongest asset
— credibility — into a liability. This is why the claim labels and the reliability ladder are gates, and
why the stdio limit is documented rather than defended.

## 4. Dismissed risks (and why)

| Dismissed risk | Why we are not managing it as a live risk |
|---|---|
| **"You'll become a vault / store customers' secrets."** | Permanent non-goal. Backends store; we broker ([PRD 05 §F](05-features.md), [PRD 20 §7](20-standards-and-claims.md)). A "secrets managed" metric is explicitly an anti-metric ([PRD 07 §6](07-success-metrics.md)). |
| **"You'll compete with the policy engine / IdP."** | Separation of duties is an invariant ([PRD 06 §3](06-security-baseline.md)): agentpolicy decides, agentkeys brokers and revokes, the enforcer enforces. We consume identity (R12); we do not issue it. |
| **"You'll be judged on prompt-injection detection."** | We do not build a detector and never claim a detection rate. Mitigation is architectural: nothing usable to steal ([PRD 06 §6](06-security-baseline.md)). |
| **"Browser / session credential capture is the bigger prize."** | Permanent refusal. Out of scope by design, not by roadmap. |
| **"Single-harness dependence."** | Structurally avoided: the broker sits **below the harness**, so env/header interception generalizes (E8, [PRD 19](19-harness-compatibility.md)). Not a risk we accept — a design constraint. |
| **"Multi-tenant SaaS scaling."** | Not in v0.1.0 (server/fleet is R11, v0.2.0). Pretending to multi-tenancy we do not have would be worse than stating the gap ([PRD 03 §4](03-landscape.md)). |
| **"Post-quantum / long-horizon crypto break."** | Tokens are short-lived (seconds–minutes) and sender-constrained at R14; the long-lived secrets live in backends/IdPs that own their own PQC timelines. Monitored, not owned here. |
| **"We are too small to matter / a platform will simply clone it."** | The moat is the invariant plus reproducible public evidence plus stdio coverage — none of which a gateway can reach on the network path. Cloning the *idea* is easy; reproducing the **proof** is the work. |

## 5. Risk → requirement coverage

| Risk | Primary controls | Requirements / invariants |
|---|---|---|
| R-1 broker compromise | Transient secrets, isolated broker, outside-control-plane, self-attack packs | I2, I6, E10, [PRD 06 §3](06-security-baseline.md) |
| R-2 stdio co-located runtime | Process-boundary requirement, recorded attempts, published gap | R8, I1, [PRD 06 §4](06-security-baseline.md) |
| R-3 backend outage | `doctor`, denial-not-corruption, no static fallback | R5, E4, E9 |
| R-4 MCP spec step-change | Upstream contribution, transport-agnostic injection | E7, [PRD 20 §3](20-standards-and-claims.md) |
| R-5 incumbent "good enough" | Local-first, free, below-harness, interoperate | E8, [PRD 03 §3](03-landscape.md) |
| R-6 platform absorption | Off-network-path, stdio coverage, evidence moat | R8, R2, [PRD 07](07-success-metrics.md) |
| R-7 adoption friction | One CLI, no cloud, no agent-code change, migration helper | F1, F17, E8, CUJ-1 |
| R-8 standards drift | Consume-not-reimplement; aligned ≠ implemented | R12, [PRD 20 §2](20-standards-and-claims.md) |
| R-9 supply-chain | Signed releases, provenance, SBOM, Scorecard, OSS-Fuzz | E15, [PRD 20 §5](20-standards-and-claims.md) |
| R-10 over-claiming | Claim labels, non-claims, gaps as first-class | [PRD 20 §6–7](20-standards-and-claims.md), [PRD 06 §6](06-security-baseline.md) |
| R-11 store corruption | Capability-gated single-writer store, `verify-log` | E2, I8, E12 |
| R-12 bus factor | Reliability ladder as buyer requirement, recruit reviewer | [PRD 20 §5](20-standards-and-claims.md) |

### Residual risk we accept

- **A same-runtime stdio process** may be readable on a harness that cannot offer a boundary (R-2). We
  document it and refuse to claim otherwise.
- **Availability during a backend outage** (R-3). Fail-closed costs some uptime; that is the trade we
  choose over silent fallback.
- **Enterprise feature breadth** (R-5). We do not build SSO, multi-tenancy, or a control plane in
  v0.1.0; we state the gap ([PRD 03 §4](03-landscape.md)).

## 6. Ownership, review cadence, and honesty

- **Owner:** the risk register is owned alongside [PRD 06](06-security-baseline.md) and revisited at every
  release gate; likelihood/impact are re-scored there, not silently inherited.
- **One new tripwire per incident.** Any incident (real or from a field-test miss) must add or tighten a
  tripwire here — the register is a living control surface, not a document.
- **Gaps are published.** Where a risk is not mitigated (R-2 in a given harness), the field-test report and
  [PRD 03 §4](03-landscape.md) state it. A risk we cannot mitigate is a miss we document, never one we
  hide.

See [PRD 09](09-roadmap.md) for how releases are gated against these risks and
[PRD 12](12-traceability.md) for risk → requirement → test traceability.
