# Article ideas — agentkeys v0.1.0 field test

One file: title, hook, and grounding facts for each. Full source: the
[field test report](../field-test/v0.1.0/FIELD_TEST_REPORT.md) — 74 cases, **69 PASS · 1 FAIL · 4 WARN** —
plus the [plan](../field-test/v0.1.0/FIELD_TEST_PLAN.md), the
[defect catalogue](../field-test/v0.1.0/FIELD_TEST_REPORT.md#defect-catalogue), and the
[field notes](../field-test/v0.1.0/FIELD_TEST_REPORT.md#field-notes--findings-learnings-and-observations).

---

## 1. Your test dashboard lies by omission

**Title.** Your Test Dashboard Lies by Omission — Here's a Verdict Vocabulary That Doesn't

**Hook.** "97% green" hides exactly the five rows a reader needs most. Our field test ran 74 cases: 69
passed, 1 failed, 4 warned — and every non-pass is named, limited, and evidenced in the published report. The
one FAIL is a Docker volume-permission bug in **our own harness**, root-caused with the fix staged. The
WARNs each cite their limitation. Nothing dropped, nothing rounded, nothing averaged.

**Grounding facts.**
- Master table: all 74 case ids with ✅/❌/⚠ and a one-line note — `FIELD_TEST_REPORT.md` §Scenario Results.
- Run-status table leads the report: 69 PASS (all grounded) · 1 FAIL · 4 WARN · 0 NOT RUN.
- Verdict vocabulary: PASS | FAIL | WARN | NOT RUN, plus the ✓-grounded qualifier (assertions re-derived
  from committed results, never trusted from an exit code).
- Honest limit: *field-tested* on one box — not *verified* (no third party has re-run it).

---

## 2. Exit code 0 is the weakest evidence you have

**Title.** Exit Code 0 Is the Weakest Evidence You Have — Make Your Verifier Re-Derive Every Claim

**Hook.** Our runner's exit code was never trusted once. An independent gate re-derives every PASS from the
committed results — each assertion's `kind` + `expected` + `actual` recomputed, `passed` re-checked,
evidence files sha256-verified. It caught a **plausible-sounding assertion that encoded a false belief about
our own product**: "no live issuance after revoke" — wrong, because revoke is an epoch CAS, not a status
flip. An exit code blesses that mistake; a re-derivation catches it.

**Grounding facts.**
- Gate: `scripts/fieldtest/check_grounding.py` → findings = 0 across all 74 results.
- The caught bug: defect H-8 in the catalogue — the assertion tested a status flip instead of the
  `revoked` event; fixed to assert the event was recorded + next-hop refused.
- Minimum depth enforced: ≥2 assertions per case, ≥3 for the five blocking cases; a PASS with no assertions
  is a finding.
- The gate is self-tested (`verify_harness.py`) on temp copies only — a destructive gate is never exercised
  on the real artifacts.

---

## 3. My leak scanner caught a real secret — in my own test harness

**Title.** My Leak Scanner Caught a Real Secret — in My Own Test Harness

**Hook.** The best moment of the sweep: the results-tree leak gate flagged **six credential shapes in the
committed evidence**. Not in the product — in **our own executor**. The FT-CL-HEADER case had stored
`Authorization: Bearer <token>` verbatim as an assertion "actual". The runner was green; the evidence was
dirty. If your security product's field harness can't pass its own scanner, what is the scanner for?

**Grounding facts.**
- Finder: `scripts/fieldtest/scan_results.py` over `field-test/v0.1.0/results/` — flagged
  `results/FT-CL-HEADER/{summary.json,summary.md,assertions.json}`.
- Fix: assert **booleans** (`headers.get(...).startswith("Bearer ")`), never rendered header values; the
  whole tree re-scanned to findings = 0.
- Related: H-7 — `_FAKE_TOKEN`/`_FAKE_SECRET` module constants tripped S105 (hardcoded-password lint) and
  were renamed `_PLANTED_VALUE` so they can never echo into an artifact.
- "Usable" is defined (shape **and** authenticates-or-is-raw-backend-secret) in
  [PRD 21 §3](../prd/21-evidence-register-and-method.md) and applied in FT-AP-CONTEXTDUMP.

---

## 4. How to publish a performance claim nobody can game

**Title.** How to Publish a Performance Claim Nobody Can Game — Kill-Time in 0.03ms

**Hook.** Our headline number is "revoke kills access in ≤1 second." The protocol that produced it is
ungameable in both directions: it measures **t0 → replay-refused** (a fast command with a still-live token
is a false green), it checks **max**, not just p95 (one bad run fails; no averaging), and it runs N≥100
**per scope**. Result: p50 0.010ms · p95 0.015ms · **max 0.030ms** — ~33,000× under budget — published with
its machine class and still labeled *field-tested*, not *verified*, because nobody else has re-run it.

**Grounding facts.**
- Protocol: [PRD 17 §15](../prd/17-scenarios.md) — t0 immediately before the revoke dispatches, t1 the
  instant a replay of the pre-revoke credential is rejected; PASS requires p95 ≤ 1s **and** max ≤ 1s.
- Result: `results/FT-RK-KILLTIME/summary.json` — p50 0.010, p95 0.0147, max 0.0298ms, N=100,
  `replay_failures == 100`.
- Machine class recorded per result in `env.json` (macOS arm64, py3.14, Docker 29.5.2, git SHA).
- The 1s budget maps to the spine gate ([PRD 07 §2.1](../prd/07-success-metrics.md)): it is CI-gated every
  commit (`tests/test_revoke_killtime.py`), not benched once for a blog post.

---

## 5. The stdio boundary is only as real as the process boundary under it

**Title.** Every stdio MCP Server Reads Credentials from Its Environment — Nobody Covers It

**Hook.** The MCP spec tells stdio servers to read credentials from the environment — which, in an agent
host, is agent-readable config: static, unscoped, unrevocable. No product covers it (coverage-map row #8).
We cover it — and we're honest about the hard case: a co-located process can read what that runtime can
read. The field topology answers it for real, in containers.

**Grounding facts.**
- FT-DK-BOUNDARY (PASS): the child container has **no mount and no readable path** to the broker store or
  the credentials volume — the probe only succeeds because both paths are absent.
- FT-DK-IMAGE (PASS): broker image non-root **UID 10001**, pinned base, secret-free Dockerfile (verified by
  the same shape scanner).
- FT-DK-SINGLEWRITER (PASS): a second broker on the same home is **refused** — single-writer (D-08)
  enforced by the OS lock, not by convention.
- The honest limit is first-class: the co-located same-runtime case is documented as **not protectable**
  ([PRD 06 §4](../prd/06-security-baseline.md)); the container boundary is the tested shape; the
  limitation is in the plan, the report, and the product docs — never a footnote.

---

## 6. Where bugs actually live: the defect taxonomy after 74 field units

**Title.** 74 Field Test Cases, 10 Defects Found — Zero Were in the Product

**Hook.** Ten defects surfaced during the sweep. **All ten were in the harness or the environment.** A
root-owned Docker named volume fighting a non-root broker (H-1). A `compose run --network` flag that doesn't
exist (H-2). An ENTRYPOINT that swallowed a probe (H-3). A leak in our own assertions (H-6). A wrong
assertion about our own revocation semantics (H-8). The product's core — bindings, fail-closed, ledger,
revocation — passed everywhere it was probed. That's the expected distribution for a v0.1.0 with a 650+-run
unit suite, and it's exactly what the deep-validation gate is *for*: the harness kept finding itself first.

**Grounding facts.**
- Catalogue: H-1…H-10 in `FIELD_TEST_REPORT.md` §Defect Catalogue — each with its finder, fix, and status.
- Product defect count: **0** across all deterministic packs (core, binding, stdio, fail-closed, killtime,
  audit, stepup, offline, attack, migrate, ops, nfr, conformance).
- The one open red: FT-DK-AIRGAP (H-1, harness environment), property covered by FT-AG-OFFLINE (PASS).
- Honest limit: "zero product defects **found**" ≠ "zero product defects exist" — it's what 74 cases on one
  box found.

---

## 7. Measured, recorded, labeled — a template for honest benchmarks

**Title.** Eight Performance Targets, Eight Crushings, Zero Roundings — an Honest Benchmark Template

**Hook.** Every NFR target was met by orders of magnitude — and recorded exactly as measured, machine class
attached, none rounded into a pass: injection p99 **0.001ms** (target <10ms), file backend **0.017ms**
(<5ms), throughput **26,988 issuances/s** (≥100/s), cold start **54ms** (<200ms), restart-to-serving
**1.486ms** (<1s), ledger append **0.012ms** (<2ms), RSS **35.1MB** (<50MB), `doctor` **4ms** (<2s).

**Grounding facts.**
- Table: `FIELD_TEST_REPORT.md` §Performance & Timings — every row carries its machine class.
- Per-case evidence: `results/FT-NFR-*/summary.json` with the p99 samples in `assertions.json`.
- Measurement discipline: p99 computed over 200–300 samples per measure; the numbers are this box only,
  stated in the table header — **never a fleet claim**.
- A missed target would have been reported as a finding with the number — none missed.

---

## 8. How to keep a human journal machine-safe

**Title.** The Report No Automation May Write — Enforced in Code, Not by Convention

**Hook.** Our field report is a hand-maintained journal — and that rule is **enforced by tests**: the file
carries a `HAND-MAINTAINED` marker, a guard proves a writer refuses it (relative *and* absolute paths — a
real prior bug where a guard missed and clobbered the file), drafts land only in
`FIELD_TEST_REPORT.generated.md`, and the runner rejects any results path under `docs/`. "No automation
writes the report" is a passing test case like any other.

**Grounding facts.**
- Guard: `tests/test_field_report_guard.py` — marker presence, builder refusal (exit 2, file untouched),
  marked-file refusal, generated-sibling-only.
- Case: FT-HONESTY-REPORT (PASS) — the guard is itself a field case with committed evidence.
- Precedent: the agentpolicy v0.1.0 report was destroyed once by exactly this bug (relative vs absolute
  `-o` path comparison) — the lesson is codified in the repo's AGENTS.md violation log.
- The sweep that filled this report never wrote a byte of it — the runner refuses the path by design.

---

## 9. The WARN is the honesty system working — not softness

**Title.** Four Warnings and a Failure Made This Report Better — Here's Each One

**Hook.** A report with zero WARNs here would be a report that lied. The fresh-box install median WARNs
because this isn't a fresh box (the scripted path ran in 0.54s). The enforce-mode case WARNs because no OS
enforcer is composed on this machine — so it **names the gap** rather than claiming a block it didn't
perform. The two harness cases WARN because wiring + smoke are green but the live Claude Code / Cursor
loops weren't automated. Each WARN cites its limitation in the committed result itself.

**Grounding facts.**
- The four WARNs + their `limitations` fields: `results/FT-CL-FIRST/`, `results/FT-EV-ENFORCE/`,
  `results/FT-HC-CLAUDE/`, `results/FT-HC-CURSOR/` — each names its plan-§8 limitation.
- Rules that make WARN honest: a WARN requires a **named limitation and a WARN-eligible class**; the five
  blocking scenarios (SC-24/40/41/43/51) may never WARN — and none did.
- The one FAIL is likewise honest: FT-DK-AIRGAP stays ❌ until the staged fix re-runs green, even though the
  gate it could block is carried by FT-AG-OFFLINE.
- "A silent skip is a FAIL of the run" — plan §2 rule 1.

---

## 10. Small batches are a durability decision

**Title.** Interrupted Mid-Run Three Times, Lost Nothing — Batches as a Durability Decision

**Hook.** The docker pack ran three times with a fix between each; the final air-gap re-run was
**interrupted mid-flight** — and nothing else was lost. Packs run one at a time, each group commits its
evidence, each group is re-runnable alone, and the gates re-derive from disk rather than trusting in-flight
state. One big `run-all` would have left half a sweep's evidence in an unknown state.

**Grounding facts.**
- Journal: `FIELD_TEST_REPORT.md` §Small-Group Run Journal, groups 1–6 — run → ground → fix → journal,
  pause between groups.
- Runner: `scripts/fieldtest/run_pack.py --pack <one pack>` — packs are independent; a crash in one
  executor becomes a FAIL result for that case, never a dead sweep (proven by the runner test).
- Cost stated honestly: the air-gap FAIL is still open **because** the last re-run didn't land — small
  batches trade latency for durability.
- The report was filled in incrementally by hand after each group, not reconstructed at the end.

---

## 11. The claims ladder — never use a stronger word than the evidence

**Title.** Documented · Conformance · Field-Tested · Verified — Never Use a Stronger Word

**Hook.** Every claim in our report carries a label: *documented* (written, no test), *conformance* (suite
green in CI), *field-tested* (a hand-entered verdict against committed evidence), *verified* (a third party
re-ran it). Kill-time ≤1s is field-tested. The RFC suites are conformance. **Nothing is verified yet** —
because `bench/` hasn't been re-run by anyone else. The claims audit maps every promoted claim to its row
and its label.

**Grounding facts.**
- Audit table: `FIELD_TEST_REPORT.md` §Claims-label audit — 13 claims, each with its label and evidence row.
- Ladder definitions: [PRD 20 §6](../prd/20-standards-and-claims.md); product-claim vocabulary §6a
  ("brokered", "audience-bound", "first-class recipe" each have exactly one meaning).
- Examples in the audit: revoke ≤1s → field-tested (FT-RK-KILLTIME); RFC 8699/8707/… → conformance
  (FT-CONF-STANDARDS); install <15 min → **documented only** (WARN — no fresh-box median); third-party
  re-runs → **not yet**, stated.
- Anti-pattern the ladder forbids: a "field-tested" claim with no hand-entered verdict; a "verified" claim
  from our own re-run of our own benchmark.

---

## 12. A credential broker with no LLM in it — and no LLM in its tests

**Title.** 74 Test Cases, Zero Model Calls — Determinism Is the Product

**Hook.** Unlike our sibling policy engine (whose field sweep drives local LLMs as oracles), the entire
agentkeys field test — 74 cases, 16 packs, a full Docker topology — contains **zero model calls**. Every
decision path is deterministic, every HTTP/exchange target is a fake service that records sha256 hashes
instead of tokens, every harness "agent" is a fixture child process. For a credential broker, determinism
isn't a nice-to-have — it's the product.

**Grounding facts.**
- Plan §2 rule 4: "No ML, no decision-affecting randomness, no network in the decision path" — the boundary
  is stated before any case runs.
- Fake upstream: `field-test/v0.1.0/docker/upstream.py` — records metadata + sha256 of auth material,
  **never a token value**; fake STS returns a fixture exchanged token.
- Fixture child: `field-test/v0.1.0/docker/child_server.py` — answers only
  `token_present`/`token_length`/`reference_present`, never echoes the token.
- Runtime deps: `dependencies = []` — stdlib-only broker (FT-SC-INREPO verifies it against `pyproject.toml`).
- The only agentic surface would be the live Claude Code / Cursor runs — and those are the **declared
  WARNs**, not silent assumptions.