# PRD 17 — Scenarios

**BLUF:** The PRD set makes claims; the **scenario catalog** is how each claim becomes a repeatable,
scored observation instead of an assertion. This document defines the **field-test scenario packs** —
core lifecycle, binding/replay, stdio MCP, evasion, fail-closed/fault-injection, revocation/kill-time,
lifecycle-audit, step-up, harness-compat, and air-gapped — plus the **attack packs** (context-dump,
evasion, and tamper-against-our-own-product) and the **kill-time benchmark protocol**. Every scenario has an
id (SC-01…SC-43 + **SC-51** for P0), a goal, a setup, a stated expected outcome, and a **PASS/FAIL/WARN** scoring
criterion; **SC-24** (revoke ≤1s) and **SC-40 / SC-43** (zero usable secrets) are release-blocking. The
scenarios are the bridge from [PRD 12](12-traceability.md) requirements to the hand-maintained field-test
report ([PRD 21](21-evidence-register-and-method.md)): a scenario is only evidence once a human records its
verdict against committed results.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. What a scenario is (and is not)

- A scenario is an **executable case** with a defined setup, a defined expected outcome, and a pass
  criterion. It is *not* a unit test: the unit/contract tests live in `tests/` and are traced in
  [PRD 12](12-traceability.md); a scenario is the **end-to-end** observation a human or the field-test
  runner performs and the report records.
- Every id here is the **same id** referenced by [PRD 12](12-traceability.md). Each maps to a requirement
  (`R#`/`E#`) and a CUJ ([PRD 04](04-users-and-cujs.md)).
- **Honesty:** a scenario that cannot be fully executed (e.g., no enforcer composed on this OS, no
  enterprise backend yet) is scored **WARN** with the limitation named — never silently PASS, never dropped.
  A scenario is *field-tested* only when the hand-maintained report carries its verdict.

## 2. Packs at a glance

| Pack | Code | Scenarios | Question it answers |
|---|---|---|---|
| Core lifecycle | **CL** | SC-01…SC-07 | Does the reference → resolve → inject → use → expire path work end-to-end? |
| Binding / replay | **BR** | SC-08…SC-11 | Is a token useless outside its `(audience, tool, session)`? |
| stdio MCP | **ST** | SC-12…SC-13 | Does a local stdio server authenticate with no secret in config/env/context? |
| Evasion | **EV** | SC-14…SC-17 | Is a raw-credential read caught (and blocked where an enforcer composes)? |
| Fail-closed / fault-injection | **FC** | SC-18…SC-23 | Does every failure deny, never degrade to a grant? |
| Revocation / kill-time | **RK** | SC-24…SC-28 | Does `revoke` land ≤1s, scoped, and auditable? |
| Lifecycle-audit | **LA** | SC-29…SC-32 | Is the whole lifecycle reconstructable and tamper-evident? |
| Step-up | **SU** | SC-33…SC-34 | Is prod-class scope impossible without an approving decision? |
| Harness-compat | **HC** | SC-35…SC-38 | Does one broker serve ≥2 harnesses and generic clients? |
| Air-gapped | **AG** | SC-39 | Do core + revoke pass with the network off? |
| **Attack packs** | **AP** | SC-40…SC-43 | Does a full compromise, or tampering with *us*, fail safe? |
| Migration & posture | **MP** | SC-51…SC-52 | Do secrets actually leave `.env` — and is the residual visible? |
| Forward slate *(planned)* | — | SC-44…SC-50, SC-53 | The P1/P2 requirements — documented, not yet built. |

---

## 3. Core lifecycle pack (CL) — R1, R2, R5, E1, E6, E7

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-01** | First brokered credential < 15 min | Fresh `AGENTKEYS_HOME`; `pip install`; `agentkeys init`; move one key to backend; replace with a reference; run the agent tool | Authenticated tool call completes with **no agent code change**; a lifecycle event appears | PASS: median install→first brokered call < 15 min over ≥5 fresh runs; no cloud account used |
| **SC-02** | Env-injection end-to-end | stdio/CLI target started under the broker; reference in place | Tool authenticates via child-process env virtualization; transcript holds only the reference | PASS: call succeeds; 0 secret bytes in transcript/args |
| **SC-03** | Header-injection end-to-end | HTTP target; reference bound to a header | Request authenticates via injected header | PASS: 2xx authenticated response; header value never visible to the agent |
| **SC-04** | RFC 8693 exchange end-to-end | Token-based downstream; session credential as `subject_token` | Downstream receives a narrow, audience-bound token | PASS: exchange succeeds; token audience == target; scope == tool op |
| **SC-05** | TTL expiry fires exactly once | Issue at a known instant; advance the clock across the TTL | Expiry event fires once; token is dead after TTL | PASS: exactly one expiry event; no post-TTL success |
| **SC-06** | Rotate without restart (CUJ-10) | Rotate the backend value mid-session | Next resolution uses the new value; agent never restarts | PASS: post-rotation call succeeds; pre-rotation token dead within TTL |
| **SC-07** | Two harnesses, one broker (CUJ-12) | Same reference used from two harnesses' egress points | Both authenticate; same bindings, same revoke | PASS: both recipes authenticate; one `revoke` kills both |

## 4. Binding / replay pack (BR) — R3, E3, E7

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-08** | Audience replay fails (CUJ-5) | Present an issued token to a **different** server (wrong RFC 8707 audience) | Replay refused; `exchange-rejected` logged | PASS: refusal + event; no second success |
| **SC-09** | Tool-scope replay fails | Present the token to a **different** tool/operation | Refused and logged | PASS: refusal + event |
| **SC-10** | Session-bound replay fails | End the session, then replay the token | Refused after session end | PASS: refusal + event |
| **SC-11** | Stale / forwarded / widened issuance fails | Replay a stale issuance; forward it; request a wider audience/scope | All three fail closed; no widening possible | PASS: all three refuse; injector cannot widen the binding |

## 5. stdio MCP pack (ST) — R8, E7, E14

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-12** | stdio authenticates with no secret in config/env/context (CUJ-4) | Local stdio MCP server launched under the broker with a placeholder; upstream API | Upstream call succeeds; server config + env + agent transcript contain **no real secret** | PASS: authenticated call; scan of config/env/transcript finds 0 usable secrets |
| **SC-13** | stdio: no token passthrough (US-18) | Server receives a client-supplied token in the request | Upstream receives a **broker-minted** scoped credential, not the client token | PASS: upstream sees a broker token; client token never forwarded |

## 6. Evasion pack (EV) — R7, E10

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-14** | `.env` read attempt caught (CUJ-6) | Agent attempts to read a `.env` outside the broker | High-severity `evasion` event; in enforce mode, blocked | PASS: event emitted (monitor-safe); blocked-and-logged where an enforcer composes (**WARN** if none) |
| **SC-15** | Cloud credential file read caught | Attempt to read a cloud credential file outside the broker | High-severity event | PASS: event emitted; path named |
| **SC-16** | Keychain read outside the broker caught | Attempt a direct keychain read | High-severity event | PASS: event emitted; attempt attributed |
| **SC-17** | Enforce-mode block + honest gap (CUJ-6) | Run the same attempts with an enforcer composed (agentkernel/agentseatbelt) | Read blocked and logged together; where uncovered, the gap is **named**, never claimed blocked | PASS: covered paths blocked+logged; uncovered paths recorded as a named gap |

## 7. Fail-closed / fault-injection pack (FC) — R5, E2, E4, E12

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-18** | Locked backend → deny (CUJ-8) | Lock the keychain; attempt issuance | Issuance **denied**; actionable error; `doctor` explains | PASS: deny on every path; no static/env fallback |
| **SC-19** | Absent backend → deny | Remove the backend / target missing | Denied | PASS: deny; no fallback |
| **SC-20** | Ambiguous / partial config → deny (CUJ-8) | Partial config readable as a fallback | Refused loudly | PASS: deny + explicit diagnostic; never "best effort" |
| **SC-21** | Corrupt store → no new issuance | Corrupt the broker store | No new issuance; `doctor` non-zero | PASS: issuance refused; no silent repair-to-allow |
| **SC-22** | Sink offline → local ledger authoritative | Take the agentwatch sink offline | Local ledger remains authoritative with a **gap marker** | PASS: gap marker present; no loss of local chain integrity |
| **SC-23** | kill -9 mid-issue → recover + exactly-once | Kill the broker during issuance; restart | Recovery; exactly-once per binding | PASS: no duplicate issuance; no orphan credential after restart |

## 8. Revocation / kill-time pack (RK) — **R4**, E3, E6, E12 (the spine)

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-24** | Revoke end-to-end ≤1s (CUJ-2) — **blocking** | Issue → `revoke` → replay the issued credential | Next exchange refuses; issued token stops authenticating; `revoked` event emitted | **PASS: kill-time p95 ≤ 1s AND max ≤ 1s over N≥100; replay provably fails** |
| **SC-25** | Scoped revoke does not over-kill | `revoke --agent` / `--session`; other agents/sessions continue | Only the target dies; others unaffected; `--all` explicit | PASS: target dead; non-targets still authenticate |
| **SC-26** | Revoke during an in-flight call | Revoke while a call is mid-flight | The call's **next hop** fails closed | PASS: next hop refused; no completion after revoke |
| **SC-27** | Revoke unknown target → error, not silence | Revoke a nonexistent agent/session | Loud error; never a silent no-op | PASS: non-zero exit; message names the unknown target |
| **SC-28** | `revoked` event carries operator identity | Revoke as a named operator | Event carries principal + target + timestamp | PASS: all three fields present in the ledger/event |

## 9. Lifecycle-audit pack (LA) — R6, E5, E12

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-29** | `export --session` reconstructs the lifecycle (CUJ-9) | Run a session incl. a rejection; export it | Ordered timeline: resolve, issue (with binding), use, step-up, revoke, + chain | PASS: every transition attributed; joins to the trace by `session_id` |
| **SC-30** | Ledger tamper detected (US-20) | Rewrite/delete a ledger row; run `verify-log` | Corruption **detected**, not skipped | PASS: non-zero verify; offending row identified |
| **SC-31** | Export contains no secret material | Scan an export for usable secrets | 0 real secrets | PASS: evidence scan finds 0 usable secrets in the export |
| **SC-32** | agentwatch event per transition | Exercise issuance/use/upgrade/revoke/reject/evade | One agentwatch-schema event each | PASS: six event types emitted with `event_version` |

## 10. Step-up pack (SU) — R9, E3

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-33** | Step-up approved (CUJ-7) | Request a prod-class upgrade; agentpolicy returns `ask`; human approves | Upgraded token minted with **tighter TTL**; `authorization.source` recorded | PASS: no upgrade before approval; provenance in ledger |
| **SC-34** | Step-up denied / timeout → no credential | Deny the request; then let `ask` time out | No upgrade, no credential on either path | PASS: both outcomes deny; agent receives a structured deny |

## 11. Harness-compat pack (HC) — E8, E1

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-35** | Tier-1 recipe A ends in an authenticated call | Apply recipe A's egress wiring | Verified authenticated call | PASS: 2xx authenticated; transcript holds only the reference |
| **SC-36** | Tier-1 recipe B ends in an authenticated call | Apply recipe B's egress wiring | Verified authenticated call | PASS: 2xx authenticated; no per-harness code fork |
| **SC-37** | Generic MCP client / custom SDK path (US-22) | Drive the broker from a generic client/SDK | Contract-level integration works | PASS: issue/use/revoke via the public contract |
| **SC-38** | Honest "not yet" for an uncovered harness | A harness with no usable interception point | Documented lower-layer coverage or an explicit "not yet" | PASS: never labeled "supported"; gap named ([PRD 19](19-harness-compatibility.md)) |

## 12. Air-gapped pack (AG) — R5, E4, E12 (CUJ-11)

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-39** | Core + revoke with the network off | Disable all networking; run SC-01 and SC-24 | Both pass; `doctor` confirms offline mode | PASS: SC-01 + SC-24 pass offline; no network call attempted; unsupported cloud backend **warns and refuses**, never silent |

---

## 13. Attack packs (AP) — R1, E5, E7, E10

Attack packs attack the **product**, not the happy path. They are the reason a reviewer can trust the
invariant, and they run in CI as regressions ([PRD 06 §7](06-security-baseline.md)).

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-40** | **Context-dump** finds zero usable credentials (CUJ-3) — **blocking** | Simulate a full compromise: dump transcript + env + args + config + logs | Only references and clearly-fake values; **0 usable credentials** | **PASS: 0 usable secrets across every variant** (see study protocol, [PRD 21](21-evidence-register-and-method.md)) |
| **SC-41** | **Tamper against our own product** fails closed — **blocking** | Edit broker config to always-allow; kill the broker; spoof a reference | Fail closed + loud event; no grant | **PASS: every tamper path denies and emits an event** |
| **SC-42** | Injector scope-widening rejected | Attempt to widen audience/scope through the injector | Widening refused at the binding | PASS: no widening; refusal logged |
| **SC-43** | **Evidence scanner**: 0 secrets in store/export/ledger — **blocking** | Scan store, exports, and ledger payloads for secret-shape material | 0 raw secrets; receipts on every redacted field | **PASS: 0 secrets found; receipts present** |

## 14. Forward-slate scenarios (SC-44…SC-50) — planned, not yet built

These are named so the trace is continuous ([PRD 12 §3–§4](12-traceability.md)); they are **documented,
not executed**, and must not be scored until the requirement lands.

| ID | Pack | Requirement | Scenario (planned) |
|---|---|---|---|
| **SC-44** | Backends | R10 (P1) | 1Password/Vault/K8s/cloud SM resolves through the pluggable contract; conformance-gated |
| **SC-45** | Server/HA | R11 (P1) | Central broker serves many agents; parent→child delegation narrows monotonically |
| **SC-46** | Identity | R12 (P1) | SPIFFE/WIMSE SVID carried as the RFC 8693 actor token; identity joined to `gen_ai.agent.id` |
| **SC-47** | Budgets | R13 (P2) | Cumulative capability caps exhausted → auto-halt via agenthalt |
| **SC-48** | Crypto | R14 (P2) | DPoP proof-of-possession: a stolen token string is insufficient |
| **SC-49** | Ecosystem | R15 (P2) | Signed MCP tool descriptions + poisoning reports consumed |
| **SC-50** | Egress | R16 (P2) | Tool outputs tagged containing secrets/PII → denied flow to external sinks |
| **SC-53** | Canaries | R19 (P2) | A canary reference planted in context fires **on first use attempt** with full attribution; the page is immediate; auto-revoke composition decided by agenthalt, never silently |

## 14a. Migration & posture pack (MP) — R17 (P0), R18 (P1, v0.1.x)

| ID | Goal | Setup | Expected outcome | Score — pass criterion |
|---|---|---|---|---|
| **SC-51** | Scan finds what the agent can read; migrate moves it (CUJ-1) | Seeded fixture repo: fake secrets in `.env`, `mcp.json`, a shell script, and one broad secret reused across two servers | Scan reports every planted candidate (masked previews + file/field), flags the broad reuse; migrate moves one secret to the keychain and rewrites every use site to a reference | PASS: **100% recall** on planted candidates, **0 printed secret values**; after migrate the original value is gone from the file and absent everywhere except the backend; re-scan shows the finding closed |
| **SC-52** *(planned — R18, v0.1.x)* | Posture makes the residual visible (US-28) | Fixture machine after SC-51 + one unbrokered MCP server left in config | `agentkeys posture` enumerates: env-resident secrets, references by backend/class, TTL config vs observed, revocations per agent, unbrokered servers | PASS: every finding class populated and matching the seed; **0 secret material** in the report; exit code and JSON agree |

## 15. The kill-time benchmark protocol (SC-24)

The single number the product is judged on. The protocol exists so the measurement is not gameable.

**End-to-end definition.** "Kill-time" is the wall-clock interval between **the operator's revoke taking
effect** and **the last credential that revoke was supposed to kill being provably dead** — not the time to
update a flag, and not the remaining TTL.

1. **t0** — a monotonic timestamp taken immediately before the `revoke` call is dispatched (same host, same
   clock domain as t1).
2. **Revoke** — `agentkeys revoke <agent|session|all>` executes and returns.
3. **Replay** — the harness **replays the exact credential minted before the revoke** (the same token
   string / reference resolution) against its bound target, and asserts a **rejection**.
4. **t1** — the monotonic timestamp at the instant the replay is rejected (the broker refuses the next
   exchange and the issued token fails to authenticate).
5. **kill-time = t1 − t0.**

**Rules.**

- **Replay proves it, not a status flag.** A revoke is only PASS if the replayed credential *fails*; a
  `revoked` event without a failed replay is not evidence.
- **N ≥ 100 iterations** per scope (`agent`, `session`, `all`); report **p50, p95, and max**. PASS requires
  **p95 ≤ 1s and max ≤ 1s**; a single max over budget is a FAIL, not an average to hide.
- **Windows covered:** revoke during an in-flight call (SC-26) and revoke for an unknown target (SC-27).
- **Continuous in CI:** the benchmark runs on every release candidate, not once at launch (R4).
- **Machine-readable output:** the bench emits JSON so a third party can diff our numbers against theirs.

## 16. Scoring rubric

| Verdict | Meaning | Effect on a release |
|---|---|---|
| **PASS** | Every pass criterion in the row is met | counts toward the release |
| **WARN** | The case ran, but a **documented limitation** applies (e.g., no enforcer composed, no enterprise backend yet) | recorded and named; does **not** count as a pass for a blocking scenario |
| **FAIL** | A pass criterion is missed | blocks the release if blocking; otherwise a tracked defect |
| **NOT RUN** | The case could not be executed here | recorded as a limitation, never inferred as PASS |

- Every scenario carries a criterion that is either **boolean** (refused / succeeded / detected) or a
  **threshold** (≤1s, < 15 min, 0 secrets). No criterion is a vibe.
- **Blocking scenarios:** SC-24 (kill-time), SC-40 (context-dump zero-secret), SC-43 (no-secret scanner),
  SC-41 (tamper fail-closed). A blocking FAIL "fixes forward" — never regenerated, never hand-waved.
- A release requires **all blocking scenarios PASS** and **no FAIL** in the executed P0 set.

## 17. Reproducibility note

- The packs are run by the documented runner (a single public command per pack); a third party with the
  same inputs should get the same verdicts. Scenarios that need an external system (a real upstream API, a
  Tier-1 harness) disclose that dependency in their setup.
- Evidence from a run lands under `field-test/<version>/results/`; the **verdict** is entered **by hand**
  into the hand-maintained report — no automation writes, regenerates, or moves the report
  ([PRD 21](21-evidence-register-and-method.md), and the repo field-test guard).
- **Honesty:** today every scenario in this catalog is **documented and planned**; none is yet
  *field-tested*, and no third party has re-run the benchmark. The catalog is the method; the report is the
  proof, and it does not exist until a human records it.

## 18. Related documents

- The requirement → scenario → test trace: [PRD 12](12-traceability.md).
- The evidence register, study protocol, and reproducibility kit: [PRD 21](21-evidence-register-and-method.md).
- The invariants behind the attack packs: [PRD 06](06-security-baseline.md).
- The CUJs these scenarios exercise: [PRD 04](04-users-and-cujs.md).
