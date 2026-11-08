# PRD 21 — Evidence & Method

**BLUF:** A security product that will not let you measure it is asking for faith. This document is how
agentkeys earns trust instead: an **evidence register** that binds every claim to an evidence type and a
**label no higher than its proof** (*documented · conformance · field-tested · verified*), the
**context-dump study protocol** that defines what "zero usable credentials" actually means, the
**kill-time measurement protocol** that defines "≤1s end-to-end", the **field-test method** — a
hand-maintained report with results under `field-test/<version>/results/` that no automation may write —
and a **reproducibility kit** so a third party can re-run the benchmark. It closes with a **non-evidence
honesty** section: what we have **not** proven, stated plainly, because a claim above its evidence is a
bug in a security product.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. How to read this document

- **Evidence type** — *what kind of proof* a claim rests on (see §2).
- **Label** — the highest confidence we may state, never above the proof ([PRD 20 §6](20-standards-and-claims.md)).
- **Where it lives** — the artifact a reviewer can inspect: a test path, a results directory, or a release
  attestation.
- **Honesty rule:** a claim with no evidence is *documented* at best. Unbuilt things are labeled **not yet**.

| Label | Means | Example | Cannot be used until |
|---|---|---|---|
| **documented** | Written in this PRD set; no test yet | a new P2 requirement | — (always allowed, as documentation) |
| **conformance** | Passes a spec/contract suite in CI | "implements RFC 8707 audience binding" | the suite is green on the release commit |
| **field-tested** | A human recorded a verdict against committed results | "install→first call < 15 min" | the hand-maintained report carries the verdict |
| **verified** | Independently reproduced by a third party | "kill-time ≤1s, re-run by X" | a third party publishes their re-run |

## 2. Evidence register

Each row is a claim a buyer or reviewer may test. **Today (v0.1.0 plan of record) the honest label for the
whole set is *documented*** — nothing is *field-tested* or *verified* yet, because the product is not built
and the hand-maintained report does not exist ([§8](#8-non-evidence--what-we-have-not-proven)).

| # | Claim | Evidence type | Label today | Where it lives |
|---|---|---|---|---|
| **EV-01** | A full context dump yields **zero usable credentials** | Attack-pack scan (context-dump) | documented | SC-40 ([PRD 17](17-scenarios.md)); `tests/test_reference_leak.py`; field-test report |
| **EV-02** | `revoke` kills all access **≤1s end-to-end** | Kill-time benchmark (replay-verified) | documented | SC-24; `tests/test_revoke_killtime.py`; bench JSON under `field-test/<version>/results/` |
| **EV-03** | The agent holds only a **reference** — no secret bytes | Reference grammar + redactor receipts | documented | `tests/test_reference_grammar.py`, `tests/test_redactor_receipts.py` |
| **EV-04** | Implements **RFC 8693 / 8707 / 9700 / 9728 / 9068 / 7636** | Spec conformance suites | documented | `tests/conformance/test_rfc8693.py` … `test_pkce.py` |
| **EV-05** | **No token passthrough**; upstream gets a broker-minted token | Conformance fixture | documented | `tests/conformance/test_no_token_passthrough.py` |
| **EV-06** | **stdio MCP** server authenticates with no secret in config/env/context | Scenario + unit tests | documented | SC-12/SC-13; `tests/test_stdio_virtualization.py` |
| **EV-07** | Every backend failure is **fail-closed** (deny, never fall back) | Fault-injection matrix | documented | SC-18…SC-22; `tests/test_failclosed_matrix.py` |
| **EV-08** | The lifecycle ledger is **tamper-evident** (hash chain) | Chain verification | documented | SC-30; `tests/test_ledger_chain.py` |
| **EV-09** | **Step-up** into prod scope is impossible without an approving decision | Scenario + tests | documented | SC-33/SC-34; `tests/test_stepup_approved.py`, `test_stepup_denied.py` |
| **EV-10** | Install → first brokered call **< 15 min**, no code change | Field test (timed) | documented | SC-01; field-test report |
| **EV-11** | **No secret material** in store/export/ledger | Evidence scanner | documented | SC-43; `tests/test_evidence_scan.py` |
| **EV-12** | The broker's **own supply chain is clean** (signed, SLSA, SBOM, Scorecard, OSS-Fuzz) | Release attestations + gates | documented | `tests/test_supply_chain.py`; release artifacts ([PRD 20 §5](20-standards-and-claims.md)) |
| **EV-13** | The benchmark is **independently reproducible** | Third-party re-run | **not yet** | reproducibility kit (§6); no external rerun exists |
| **EV-14** | Meaningful customer **field data at scale** | Customer deployments | **not yet** | none — no customer field evidence yet |

**Reading the register:** EV-01…EV-12 are *planned P0 evidence* — each has a defined method below; they
become *conformance* when the suite is green and *field-tested* only when the report records a verdict.
EV-13 and EV-14 are explicitly **not yet**: we name the gap rather than borrow a label.

## 3. The context-dump study protocol (EV-01 / EV-11)

**Objective.** Prove that an adversary who fully compromises the agent's context gets **nothing usable** —
the never-in-context invariant (R1 / I1).

1. **Simulate a full compromise.** Assume the attacker wins completely and collects *every* artifact the
   agent's world exposes: the model transcript, tool arguments and results, the process environment, agent
   and harness config files, generated code and files, application logs, and the broker's own export +
   ledger for the session. Assume no artifact is out of reach.
2. **Scan with two independent checks.** (a) A **pattern + shape** scanner for credential shapes (API-key
   and bearer formats, private keys, connection strings, cloud credentials). (b) A **resolves?** check: does
   the candidate string actually authenticate to its target (or is it a raw backend secret)?
3. **Define "usable".** A string is **usable** only if it (a) matches a credential shape **and** (b) either
   authenticates to a target or is a raw backend secret. A **reference** is *not* usable — it is opaque,
   broker-only, and carries no secret bytes ([PRD 11](11-decisions.md) D-04). A clearly-fake test value is
   not usable.
4. **Scanner-sensitivity control (falsification).** At least one variant **deliberately seeds** a
   should-be-caught secret. If the scanner does not flag it, the run is a **harness failure**, not a pass —
   a silent scanner proves nothing.
5. **Verdict.** **Any** usable credential found in **any** variant is a **build failure** (blocking SC-40),
   not a warning. The pass condition is **0 usable credentials** across every PRD-scenario variant.
6. **Output.** A secret-free report: variant, artifact count, redaction receipts (field, class, count),
   and the scanner-sensitivity result. Never the secret values themselves.

## 4. The kill-time measurement protocol (EV-02)

**Objective.** Make "≤1s" a measurement, not a slogan. Full case protocol in [PRD 17 §15](17-scenarios.md);
the method in brief:

- **End-to-end, replay-verified.** Measure **t0** (immediately before `revoke` is dispatched) to **t1**
  (the instant a **replay of the pre-revoke credential is rejected**), on **one monotonic clock**. A
  revoke is only a pass if the replayed credential **provably fails** — a status flag is not evidence.
- **N ≥ 100** iterations per scope (`agent`, `session`, `all`); report **p50, p95, max**; PASS requires
  **p95 ≤ 1s and max ≤ 1s**.
- **Windows:** revoke during an in-flight call and revoke for an unknown target.
- **Continuous:** the bench runs on every release candidate, not once at launch.
- **Machine-readable:** JSON output so a third party can diff our numbers against theirs (§6).
- **Scopes are not over-killed:** a scoped revoke must not kill a non-target (SC-25).

## 5. The field-test method

The field test is the bridge from *conformance* to *field-tested*. It is deliberately manual at the
verdict layer, because a lossy automated rewrite of human notes has destroyed honest evidence before.

- **The report is a hand-maintained journal** at `docs/field-test/<version>/FIELD_TEST_REPORT.md`. It
  carries a `HAND-MAINTAINED` marker. **No script, generator, CLI, agent, or task may write, rewrite,
  regenerate, move, truncate, or delete it** — there is **no "force" exception**.
- **Results live under `field-test/<version>/results/`**, never under `docs/`. The plan and the
  hand-maintained report live under `docs/field-test/<version>/`; raw results live alongside the packs.
- **Verdicts are entered by hand** from the committed results. Nothing is inferred, auto-filled, or
  "cleaned up". A verdict, a miss, a limitation, and a note are all hand-written.
- **If an automated draft is ever added**, it writes a **separate** `FIELD_TEST_REPORT.generated.md`
  sibling and **refuses** to overwrite any file carrying the `HAND-MAINTAINED` marker.
- **A report-guard test** asserts the marker and the refusal behavior; the guard ships with any writer.
- **Verdict classes** follow the scenario scoring ([PRD 17 §16](17-scenarios.md)): **PASS / FAIL / WARN /
  NOT RUN**, with blocking scenarios fixed forward by hand — never regenerated from results.

The field-test scenario catalog ([PRD 17](17-scenarios.md)) is the method; the hand-maintained report is
the proof. **The report does not exist yet**, so no scenario is *field-tested* today.

## 6. The reproducibility kit

So that a claim can be checked, not trusted:

| Piece | What it gives a third party |
|---|---|
| **Public runner** | A single documented command per pack (core, revocation/kill-time, context-dump, fault-injection) |
| **Shipped packs** | The attack packs and the kill-time bench distribute in-repo, not as a service |
| **Pinned environment** | Documented OS, runtime, and dependency pins so the run is deterministic |
| **No network** | Core and kill-time packs run air-gapped ([PRD 17 §12](17-scenarios.md)) |
| **Hardware disclosure** | The machine class used for published numbers, so comparisons are honest |
| **Machine-readable output** | JSON results + a results template under `field-test/<version>/results/` |
| **Procedure** | Steps to re-run, capture, and publish — including how to file a divergent result |

**Honesty:** this kit is the **method we will ship**; no third party has re-run it yet, so nothing is
labeled *verified* ([§8](#8-non-evidence--what-we-have-not-proven)).

## 7. How any claim is published

1. Run the scenario / suite and commit the **raw results** under `field-test/<version>/results/`.
2. Have a human enter the **verdict** in the hand-maintained report, with the limitation named if any.
3. Publish the **claim with its label** — never above the evidence ([PRD 20 §6](20-standards-and-claims.md)).
4. If a claim needs *verified*, capture the **third-party re-run** and cite it.

## 8. Non-evidence — what we have **not** proven

Stated plainly, because each of these is a real gap a reviewer should hold us to:

- **Not built yet.** v0.1.0 is the design of record; there is no shippable artifact, no green release gate,
  and no field-test report. Every P0 claim is *documented*, not *conformance* or *field-tested*.
- **No third-party re-run.** The benchmark has not been independently reproduced; nothing carries the
  *verified* label.
- **No field-tested kill-time at a customer.** The ≤1s figure is a design target and (once built) a CI
  measurement; it has not been observed in a customer's environment.
- **No compliance certification.** We **map** to SOC 2 / ISO 42001 / ISO 27001 / EU AI Act Art. 14; we are
  **not** certified. SOC 2 Type I→II is a roadmap item ([PRD 20 §5](20-standards-and-claims.md)).
- **No independent security audit or pen-test yet.** The threat model in [PRD 06](06-security-baseline.md)
  is our own; it is not a third-party assessment.
- **No fuzzing results yet.** OSS-Fuzz targets for the reference grammar and MCP/JSON-RPC frames are
  planned, not run.
- **No scale or soak evidence.** No long-duration run, no enterprise fleet (server mode is R11, unbuilt).
- **No Windows or enterprise-backend evidence.** macOS/Linux first; cloud/enterprise backends are R10,
  unbuilt.
- **No detection-rate claims.** We do not claim an injection classifier or an evasion detection *rate*;
  evasion scenarios are pass/fail on the paths we cover, with uncovered paths named.
- **No customer data.** This repository contains no real credentials and no production evidence; only
  references and clearly-fake test values.

## 9. Related documents

- The scenarios these methods score: [PRD 17](17-scenarios.md).
- The requirement → scenario → test trace: [PRD 12](12-traceability.md).
- The invariant the context-dump study protects: [PRD 06 §1](06-security-baseline.md).
- The claims vocabulary and standards gate: [PRD 20](20-standards-and-claims.md).
- The frozen decisions behind the methods: [PRD 11](11-decisions.md).
