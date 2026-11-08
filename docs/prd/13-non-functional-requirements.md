# PRD 13 — Non-Functional Requirements

**BLUF:** agentkeys is a security product, so its non-functional properties *are* its product: the two that
gate everything are **revocation end-to-end ≤1s** and **zero usable secrets in agent context** — both
CI-gated, not aspirational. Around those, the NFRs are deliberately small and boring: the broker is a
**stdlib-only, local-first, single-binary** process with **no cloud dependency**, a **crash-safe
single-writer store** with **exactly-once issuance**, a **tamper-evident ledger**, and **fail-closed**
behavior on every failure path. Egress injection adds **<10 ms p99** locally (a target, not yet measured);
install→first brokered call is **<15 min**. Every target below carries an honest label — *target* ·
*conformance* · *verified* — and nothing is claimed above its evidence ([PRD 20](20-standards-and-claims.md)).

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. How targets are labeled

| Label | Means | Evidence |
|---|---|---|
| **target** | a design goal we hold ourselves to; **not yet measured** | none yet — treat as a promise |
| **conformance** | a deterministic suite (or CI replay) gates it on every commit | the named test/suite |
| **verified** | independently reproduced by a third party | external re-run ([PRD 21](21-evidence-register-and-method.md)) |

References: requirements **R#/E#** ([PRD 05](05-features.md)); invariants **I#** ([PRD 06](06-security-baseline.md)).
"Not yet" is a first-class answer — never rounded up to "done".

## 2. Performance

| Metric | Target | Label | Verified by |
|---|---|---|---|
| **Revoke end-to-end** (issue → revoke → replay fails) | **≤1 s, worst case** | conformance | `tests/test_revoke_killtime.py` (CI replay) |
| Egress injection, **env virtualization** | **<10 ms p99** added, local | target | not yet measured |
| Egress injection, **HTTP header** | **<10 ms p99** added, local | target | not yet measured |
| Egress injection, **RFC 8693 exchange** | **<50 ms p99** added, local/intra-region | target | not yet measured |
| Backend resolution, **OS keychain** | **<5 ms p99** | target | not yet measured |
| Backend resolution, **credential file** | **<1 ms p99** | target | not yet measured |
| Broker cold start | **<200 ms p99** | target | not yet measured |
| Issuance throughput (single local process) | **≥100 issuances/s** sustained | target | not yet measured; fleet mode is R11 |
| Ledger append | **<2 ms p99** | target | not yet measured |
| Idle broker RSS | **<50 MB** | target | not yet measured |

**Method (when measured):** reference macOS/Linux laptop, warm process, local backends; the only network in
the critical path is the downstream the token is minted *for*, which is excluded from the injection budget.
The **≤1 s revoke** number is different in kind from the rest: it is the product's headline invariant and is
**CI-gated every commit**, not a one-off benchmark.

## 3. Reliability & durability

| Property | Target | Label | Requirement |
|---|---|---|---|
| **Crash-safe store** | `kill -9` mid-issue → restart **recovers**; no partial issuance | conformance | E2 |
| **Exactly-once issuance** | a duplicate request returns the **same** record; nothing re-injected | conformance | E1, E2, E3 |
| **Ledger integrity** | hash chain verifies; a **tampered row is detected, not skipped** | conformance | R6, E12 |
| **Fail-closed** | store/backend down or ambiguous → **deny issuance**, never fail open | conformance | E4, I2 |
| **Durable single-writer store** | SQLite (WAL) reference; a driver that cannot guarantee atomic single-use issuance is **refused at load**, never at runtime | conformance | E2 |
| **Export determinism** | same inputs → byte-identical export | conformance | E12 |
| Restart-to-serving | **<1 s** | target | — |
| Availability | local single-process; **no SLA at v0.1.0** (HA/fleet is R11) | documented | — |

Durability is single-writer by design: correctness over concurrency. Where a store driver cannot promise
**atomic single-use issuance**, the core refuses to start with it — a policy, not a runtime surprise (E2).

## 4. Security (summary — full analysis in [PRD 06](06-security-baseline.md))

The invariants from [PRD 06](06-security-baseline.md) §1 as NFRs. **A regression on any of these is a
release blocker.**

| # | Invariant | NFR form | Label |
|---|---|---|---|
| **I1** | Never-in-context | context-dump pack finds **0 usable secrets** across every scenario variant | conformance |
| **I2** | Fail closed | fault-injection matrix: **every** failure path is deny-or-pending | conformance |
| **I3** | Revocation unconditional | `revoke` is never gated on policy and never depends on TTL expiry | conformance |
| **I4** | Single-use, bound issuance | replay / forward / stale / cross-bound all **fail closed** | conformance |
| **I5** | No token passthrough | upstream receives a **broker-minted** token, never the client's | conformance |
| **I6** | Outside the agent's control plane | tamper (edit config / kill broker / spoof reference) → fail closed + loud event | conformance |
| **I7** | Redaction before persistence | evidence scanner finds **0** secrets in store / export / ledger; receipts on every redaction | conformance |
| **I8** | Tamper-evident record | chain verification detects a rewritten row | conformance |
| **I9** | Time cannot be gamed | clock-skew fixtures cannot extend or resurrect a TTL | conformance |
| **I10** | Supply chain is clean | signed releases, SLSA provenance, pinned deps, SBOM, Scorecard A | target → conformance (E15) |

STRIDE, the "we are a target" threat model, the stdio boundary, and the **non-claims** live in
[PRD 06](06-security-baseline.md) — this document does not restate them.

## 5. Size & portability

| Property | Target | Label |
|---|---|---|
| **Runtime dependencies** | **stdlib-only** for the broker core; no mandatory third-party service | target |
| **Distribution** | single CLI entry point (`agentkeys`), `pip install agentsec-agentkeys` | documented |
| **Platforms** | **macOS + Linux** at v0.1.0; Windows **not yet** | documented |
| **Cloud dependency** | **none** — works **air-gapped** (no tenant, no SaaS, no account) | documented |
| **Footprint** | small binaries + a single-file store; no daemon beyond the local broker process | target |
| **Store portability** | single-file SQLite; portable JSONL export | documented |

Portability is the anti-lock-in NFR: a broker you cannot run on a laptop, offline, without an account is not
the broker this product is ([PRD 00](00-press-release.md)).

## 6. Observability

| Property | Target | Label | Requirement |
|---|---|---|---|
| **Lifecycle events** | every issuance / use / upgrade / revocation / rejection / evasion emitted in the **agentwatch schema** | conformance | R6, E12 |
| **Local ledger** | append-only, hash-chained, and **authoritative even if the external sink is down** (gap marker) | conformance | R6, E12 |
| **Export** | `agentkeys export --session` → ordered, deterministic JSONL timeline | conformance | E12 |
| **Verify** | `agentkeys verify-log` returns **non-zero** on a chain break | conformance | E12 |
| **Health** | `agentkeys doctor` explains the effective backend + failure semantics; **non-zero** when unhealthy | conformance | E4 |
| **OTel** | GenAI semconv spans (`gen_ai.tool.name`, `gen_ai.agent.id`) | conformance | [PRD 20](20-standards-and-claims.md) |
| **Metrics** | kill-time + issuance counters exposed for the reproducible benchmark | documented | R4 |

Everything is **local-first**: the ledger is the source of truth, and a missing sink **never** becomes a
missing record.

## 7. Usability

| Property | Target | Label |
|---|---|---|
| **Install → first brokered call** | **<15 min** (CUJ-1) | target (field-tested only after the report) |
| **Commands to first success** | ≤3 (`init`, point a reference, run) | target |
| **Safe by default** | fail-closed, short TTLs, redaction-on, no cloud account | target / conformance |
| **Error clarity** | a malformed reference names the **failing field**; diagnostics are actionable | conformance (E1) |
| **Recipes** | one documented recipe per shipped Tier-1 harness | documented |

The bar is persona **Sam** (P4): a solo developer on one machine, three harnesses, five minutes, sane safe
defaults. If it needs a cloud account or a manual policy file to work, it fails this NFR.

## 8. Maintainability

| Property | Target | Label |
|---|---|---|
| **Typed, versioned contracts** | reference + issuance + backend + store contracts are typed and versioned | conformance (E1, E11) |
| **Conformance suites** | every implemented standard has a suite that **gates the release** | conformance (E13) |
| **Versioning discipline** | schemas **additive-only** within v0.x; `event_version` per event; old store **migrates or refuses loudly** | conformance (E11) |
| **Docs-as-tests** | examples/fixtures in the docs are validated, not decorative | target |
| **Single source of truth** | schema, event vocabulary, compatibility matrix each have one owning module | process |
| **Regression attack packs** | context-dump, evasion, tamper packs run in CI on every change | conformance |

## 9. Privacy

| Stored | Never stored |
|---|---|
| References (opaque handles) | **Secret material of any kind** |
| Bindings (`audience`, `tool`, `session_id`) | Raw tool arguments containing secrets (**redacted with receipts**, E5) |
| Timestamps, TTLs, class | Full customer records / **PII** |
| Lifecycle events (issuance/use/upgrade/revoke/reject/evade) | Credential values in logs, exports, or events |
| Principal/operator identity for actions | Browser/session credentials (**permanent refusal**) |

- **Redaction runs before storage, rendering, export, and events** (E5); every redaction emits a receipt.
- **Exports are secret-free by scan** (E12); telemetry is **local by default** with no phone-home.
- Redaction-by-default means privacy is a property of the pipeline, not a config flag someone forgets
  ([PRD 06](06-security-baseline.md) §5).

## 10. Accessibility (CLI output)

| Property | Target | Label |
|---|---|---|
| **Color is never the only signal** | every color cue has a text/shape equivalent; respects `NO_COLOR`; `--no-color` | target |
| **Machine-readable** | `--json` for scripting; **stable exit codes** | target |
| **Screen-reader-friendly** | plain, linear text output; no cursor-addressing-only UI required | target |
| **Time display** | UTC ISO-8601 (locale-independent, unambiguous) | target (E6) |
| **Terminal-agnostic** | wraps to width; no fixed-width-only layout required | target |

A credential notification a human cannot read in a terminal is a security NFR problem, not a cosmetic one.

## 11. Compliance-oriented NFRs

| Property | Target | Label |
|---|---|---|
| **Auditability** | any credential's lifecycle is reconstructable **per session** with principal, binding, and timestamps | conformance (R6, E12) |
| **Provable fail-closed** | the fault-injection matrix is a **CI gate**; every path is deny-or-pending | conformance (E4) |
| **Evidence** | a reproducible benchmark (kill-time + context dump) any third party can re-run | target → **verified** on external rerun ([PRD 21](21-evidence-register-and-method.md)) |
| **Attribution** | `revoked` events carry **operator identity**; every event is attributed | conformance (R6) |
| **Standards conformance report** | **published green on the release commit**; unsupported standards labeled, not implied | conformance (E13) |
| **Framework mapping** | controls mapped to OWASP / NIST / ISO 42001 / EU AI Act Art. 14 | documented ([PRD 20](20-standards-and-claims.md)) |

These are the NFRs persona **Dana** (P3, compliance/GRC) and **Ravi** (P2, security) consume: auditability
and provable fail-closed, not a certificate ([PRD 20](20-standards-and-claims.md) §7 non-claims).

## 12. NFR summary — target vs verified today

| NFR | v0.1.0 target | Verified today? |
|---|---|---|
| Revoke ≤1s | ≤1s worst case | **conformance** — CI replay; field-test pending |
| Zero usable secrets | 0 across all variants | **conformance** — context-dump pack |
| Fail-closed | every failure path denies | **conformance** — fault-injection matrix |
| Exactly-once issuance | same record on retry | **conformance** |
| Ledger integrity | tamper detected | **conformance** |
| Injection latency | <10 ms p99 local | **target** — not yet measured |
| Install → first call | <15 min | **target** — field-test pending |
| stdlib-only, no cloud, offline | yes | **documented** |
| Auditability / attribution | per-session reconstruction | **conformance** |
| Supply chain (E15) | signed + SLSA + SBOM + Scorecard A | **target** → conformance during v0.1.0 |

Nothing in the right column is "done" until the named gate runs green on the release commit, and no NFR is
promoted to **field-tested** or **verified** without the hand-maintained field-test report
([PRD 21](21-evidence-register-and-method.md)).
