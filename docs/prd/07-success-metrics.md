# PRD 07 — Success Metrics

**BLUF:** agentkeys is judged by three facts a skeptic can reproduce, not by a dashboard: a credential
dies in **≤1s** when an operator says so, a full **context-dump of the agent's world finds zero usable
secrets**, and credentials actually **leave `.env` for real backends**. Everything else in this document
exists to keep those three honest. We publish a **reproducible benchmark** (context-dump + kill-time) so
the headline numbers are independently re-runnable, and every metric carries an evidence label —
*documented · conformance · field-tested · verified* — never a number above the proof behind it. This is
the measurement plan for the requirements in [PRD 05](05-features.md), the journeys in
[PRD 04](04-users-and-cujs.md), and the claims vocabulary in [PRD 20](20-standards-and-claims.md).

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Why these metrics (and not the usual ones)

- **One number is the spine.** Kill-time. The product exists to make "the agent leaked its key" a
  one-second command ([PRD 01](01-why.md), CUJ-2). If a launch number does not move that or the
  zero-secret invariant, it is a vanity metric.
- **The invariant is binary, not a rate.** A context dump either finds a usable credential or it does
  not. "We reduced secret exposure by 87%" is not a thing we will ever claim.
- **Adoption is direction, not a percentage.** The point of the broker is that credentials *stop living
  in `.env`*. We measure the *funnel* and report the direction honestly; we do not set a vanity target.
- **We measure to the failed replay, not to the command.** A `revoke` that returns fast while a stale
  token still authenticates is a false green. Every headline number is end-to-end.
- **No metric may reward a gap.** Where we cannot cover a path (a co-located stdio process,
  [PRD 06 §4](06-security-baseline.md)), the metric names the gap — it is never smoothed into a coverage
  number we cannot defend.

## 2. Headline metrics

| Metric | What it measures | v0.1.0 target | How it is collected | Benchmark location | Label today |
|---|---|---|---|---|---|
| **Kill-time** | alert-ack → credential provably dead (next exchange refuses **and** an already-issued bound token fails replay) | **≤1s end-to-end** | kill-time harness: issue → revoke → tight-loop replay until refusal; runs **continuously in CI** (R4) | planned `bench/killtime/` + `tests/test_revoke_killtime.py` | documented (target) |
| **Zero-usable-secret invariant** | usable credentials recovered from a full context-dump pack | **exactly 0**, every scenario variant | context-dump pack: transcript + env + args + generated code + config + logs, scored for *usable* values; CI-gated (R1) | planned `bench/context-dump/` + `tests/test_reference_leak.py` | documented (target) |
| **Backend-migration funnel** | fraction of a team's brokered creds resolved from supported backends vs still resident in `.env`/env/config | **monotonic out of `.env`** | `agentkeys doctor` reports backend source per reference; opt-in aggregate (never secret values); field-test interviews | `agentkeys doctor` fixture + field-test report | documented (target) |

### 2.1 Kill-time (the spine)

- **Why end-to-end:** a P99 on the `revoke` command would hide the real failure — a ridiculously fast
  command that leaves a live token behind. We clock from the operator's confirmed alert to the moment a
  **replay attempt fails**, so TTL expiry cannot masquerade as revocation.
- **Continuous, not launch-only:** the harness runs on every commit and in the field-test run, so a
  regression in the revocation path is caught before a release, not benchmarked once for a blog post.
- **Scoped kills count:** `agentkeys revoke <agent|session|all>` must not over-kill. A scoped kill that
  kills more than asked is a miss, and the metric records it ([PRD 05 R4](05-features.md)).

### 2.2 Zero-usable-secret invariant (the invariant)

- **Usable, defined:** a recovered value that successfully authenticates a real call. Secret-*shaped*
  strings are counted separately (target also 0) but "usable" is the invariant — it cannot be gamed by a
  redactor that merely looks busy.
- **Every variant:** stdio MCP, HTTP header, and token-exchange egress; enforce and monitor modes; two
  harnesses; air-gapped ([PRD 04](04-users-and-cujs.md) CUJ-3, CUJ-4, CUJ-6).

### 2.3 Backend-migration funnel (the adoption proof)

- **Direction, not a vanity percentage:** we report what fraction moved out of `.env` and how fast, and
  we are honest when a team keeps a fallback. A high "secrets managed" number would actually signal we
  drifted into being a vault — see §6.
- **What "out of `.env`" means:** the reference resolves from OS keychain, credential file, or (R10) a
  secret manager; the raw value is not present in the agent's readable runtime.

## 3. Spine metrics

| Metric | Definition | Target | Evidence label |
|---|---|---|---|
| **Time-to-first-brokered-call** | `pip install` → a real authenticated tool call, no agent-code change | **<15 min** | **field-tested** (CUJ-1) |
| **Step-up resolved without widening** | share of step-up (`ask`) flows resolving to a grant **no broader** than the requested class/tool/audience | **100% no-widening** — a widening is a bug, not a rate to maximize | conformance |
| **Tier-1 harnesses covered** | named recipes ending in a verified authenticated call (E8) | **≥2 at v0.1.0, all 5 by v0.3.0** | field-tested |

- **Time-to-first-brokered-call** is the only metric we are content to call *field-tested*: it needs real
  humans on real machines. The hand-maintained field-test report is the source of truth, and **no
  automation writes it** (repo `AGENTS.md`); the number is entered by hand from committed evidence.
- **Step-up no-widening** is a correctness property, not an optimization target: if an approval ever
  grants more than asked, that is a release blocker ([PRD 05 R9](05-features.md)).

## 4. Gate-trust metrics

These are the metrics that decide whether the product is safe to ship. All are **conformance**: pass the
suite or the release is blocked.

| Metric | Definition | Target | Source |
|---|---|---|---|
| **Evasion detections caught** | R7 fixtures (raw `.env`/file/keychain reads outside the broker) flagged as high-severity, blocked where an enforcer composes | **100% of the pack**; gaps **named**, never absorbed | `tests/test_evasion_detect.py`, `tests/test_evasion_enforce.py` |
| **Token-passthrough attempts rejected** | upstream must receive a broker-minted token, never the client's (E14) | **100% of fixtures** | `tests/conformance/test_no_token_passthrough.py` |
| **Fail-closed fault-matrix pass rate** | E4 cells — locked/absent backend, corrupt store, sink offline, partial config | **100% deny-or-pending**; never allow, never silent | `tests/test_failclosed_matrix.py` |

- An **evasion detection** counts only when we can point at the path we covered. Where no enforcer covers
  a path, the fixture records the attempt and the gap; the metric reports the gap explicitly
  ([PRD 06 §4](06-security-baseline.md)).
- **Fail-closed** is measured as a matrix, not a happy path: the interesting result is the failure cell,
  not the success cell.

## 5. Product-health metrics (operations, not success)

These tell an operator whether the broker is healthy. None of them is a target we "grow"; a rising
number is usually a signal to investigate, not celebrate.

| Metric | Definition | Healthy signal | Source |
|---|---|---|---|
| **Revocation events per agent** | revocations attributed to an agent/session, per window | near-zero; a **spike is an incident or misconfig** | ledger (R6), `agentkeys export` |
| **TTL distributions** | per-class TTL histograms (floor/ceiling enforced, E6) | inside configured bands; warn on long tails | issuance ledger |
| **Backend health** | resolve success/latency/fail-closed rate per backend (E9 `health`) | failing backends **show as failing**, never degrade silently | `agentkeys doctor` |
| **Ledger verification rate** | share of sessions whose hash chain verifies (I8, E12) | **100%**; any non-verify is a **security event**, not a data-quality blip | `agentkeys verify-log` |

## 6. Anti-metrics (what we refuse to optimize)

| Anti-metric | Why we refuse it |
|---|---|
| **Number of secrets vaulted / managed** | We are **not a vault** — backends store, we broker ([PRD 05 §F](05-features.md), [PRD 20 §7](20-standards-and-claims.md)). A growing "secrets under management" number means we drifted into storage; we deliberately do not grow it. |
| **Notification / alert volume** | A detector's vanity metric. More alerts is not progress; **fewer, higher-severity, actionable** events is the goal. Success looks like silence. |
| **"Detection rate" claims** | We do not claim an injection-detection rate at all — mitigation is **architectural**, not a classifier ([PRD 06 §6](06-security-baseline.md)). Any "we catch X% of attacks" figure is an anti-metric. |
| **Schema/feature count** | Neither is a proxy for safety. A larger surface is a larger attack surface; scope may only shrink (§8 of [PRD 09](09-roadmap.md)). |

## 7. Measurement infrastructure

- **Where the benchmark lives.** A single **reproducible, containerized benchmark** (context-dump pack +
  kill-time harness) is planned at `bench/`; it is the artifact a third party re-runs to make a claim
  *verified* rather than *conformance*. It is the same evidence the field test references, and it is
  scheduled for v0.1.0 (see the reproducibility row in [PRD 20 §5](20-standards-and-claims.md)).
- **CI is the primary collector.** Kill-time, context-dump, evasion, passthrough, and the fail-closed
  fault matrix run **in CI**, so a regression blocks the commit — not a quarterly report.
- **The field-test report is hand-maintained.** Real-machine, human-observed results (time-to-first-call,
  harness coverage, backend-migration interviews) are recorded **by hand** in
  `docs/field-test/<version>/FIELD_TEST_REPORT.md`, with committed evidence under
  `field-test/<version>/results/`. Verdicts are entered by hand; automation never writes or rewrites the
  report (repo `AGENTS.md`).
- **Telemetry is opt-in and secret-free.** Aggregate counters only — never references, never values,
  never agent-controlled strings unescaped ([PRD 06 §3](06-security-baseline.md)).

### 7.1 Metric → source → evidence ladder

| Metric | Primary source | Cadence | Ladder |
|---|---|---|---|
| Kill-time | CI kill-time harness | every commit | conformance → **verified** (reproduced) |
| Zero-usable-secret | CI context-dump pack | every commit | conformance |
| Backend-migration funnel | `agentkeys doctor` + field test | per release | field-tested |
| Time-to-first-brokered-call | hand-maintained field-test report | per release | field-tested |
| Step-up no-widening | conformance fixtures | every commit | conformance |
| Tier-1 harness coverage | recipes + field test | per release | field-tested |
| Evasion / passthrough / fail-closed | conformance suites | every commit | conformance |
| Health (revoke, TTL, backend, ledger) | ledger + `doctor` + `verify-log` | continuous (local) | documented |

## 8. How a number becomes a claim

1. **documented** — written here with a target. This is where every metric starts today (v0.1.0 has *no
   shipped code*, so **no headline metric is yet conformance-, field-tested-, or verified**).
2. **conformance** — the metric's suite passes in CI on the release commit.
3. **field-tested** — observed on real machines and entered by hand in the field-test report.
4. **verified** — an independent party re-runs the reproducible benchmark and reproduces the result.

> We will not use a higher label than the evidence. Until the benchmark and CI harness exist, every
> number in this document is a **target**, marked *documented* — and we will say so out loud rather than
> imply a result we have not produced.

See [PRD 09](09-roadmap.md) for when each metric's evidence is expected to move up a label, and
[PRD 21](21-evidence-register-and-method.md) for the evidence register and the context-dump study protocol.
