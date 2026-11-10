<!-- HAND-MAINTAINED DOCUMENT — edit by hand only.
     No script, generator, CLI, agent, or task may write, rewrite, regenerate, move, truncate,
     or delete this file. There is no "force" exception (AGENTS.md, PRD 21 §5).
     Automated drafts write FIELD_TEST_REPORT.generated.md only, and refuse any file carrying
     this marker (see tests/test_field_report_guard.py). -->

# agentkeys v0.1.0 — Field Test Report

> **Status: NOT STARTED (0/74 verdicts).** This is a **hand-maintained** journal, updated as the field test
> runs — not a generated scoreboard. Counts here are read from the committed
> `field-test/v0.1.0/results/` verdicts and written **by hand**; nothing is auto-overwritten.
> **Current:** **0 ✅ PASS · 0 ❌ FAIL · 0 ⚠ WARN · 0 ▫ NOT RUN** (0/74 — nothing has run yet).
> **Structure:** follows the format of the `agentpolicy` v0.1.0 `FIELD_TEST_REPORT.md` (a journal, not a
> scoreboard), pointed at [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) §4 (case matrix), §5 (coverage),
> §6 (blocking specs), §9 (gates). This report states **honestly** what was tested, what passed, and what
> was **not** run. Verdicts are entered by hand from committed evidence; a `WARN` always names its §8-plan
> limitation; a blocking case (SC-24/40/41/43/51) may never be WARN or NOT RUN.
> **Reviewer:** (fill: name) · **Date opened:** 2026-11-09 · **Last hand-edit:** (fill)

---

## BLUF + Release Gate Verdict

> (fill when the sweep starts: current totals — X PASS · Y FAIL · Z WARN · N NOT RUN, of 74. One paragraph:
> what ran, what the Docker topology proved, which blocking scenarios are green, what is honestly not run.)

### Run status (0/74 verdicts)

| | Count |
|---|---|
| PASS (raw verdict) | 0 |
| — of which grounded (assertion re-derived from the committed results, not exit-0) | 0 (0 over-claimed) |
| FAIL | 0 |
| WARN (P/F\|W with a §8-plan limitation named) | 0 |
| NOT RUN | 74 |
| Removed from scope (not claimed as supported) | 0 |
| N/A (retired) | 0 |

**Verdict vocabulary:** **PASS | FAIL | WARN | NOT RUN** — plus the qualifier **✓ grounded** (the asserting
check re-derived from the committed `summary.json`/ledger, not the runner's exit code). A PASS that is not
grounded is treated as **not proven**. **Class:** **P/F** = hard gate · **P/F|W** = pass/fail-or-WARN (a named
limitation is the only honest alternative; never a silent skip). `WARN` is forbidden for the blocking five.

### Release gate verdict ([PRD 07](../../prd/07-success-metrics.md) / [PRD 09 §3](../../prd/09-roadmap.md); filled as the sweep runs)

| # | Gate | Status | Evidence / honesty |
|---|---|---|---|
| 1 | **Kill-time ≤1s end-to-end, replay-verified, in CI** (SC-24, blocking) | ▫ pending | FT-RK-KILLTIME — p95 AND max over N≥100/scope |
| 2 | **Context-dump finds 0 usable credentials** (SC-40, blocking) | ▫ pending | FT-AP-CONTEXTDUMP — every variant + falsification control |
| 3 | **Fail-closed matrix 100% deny-or-pending** (E4) | ▫ pending | FT-FC-* (locked/absent/config/store/sink/crash) |
| 4 | **Evidence scanner: 0 secrets in store/export/ledger** (SC-43, blocking) | ▫ pending | FT-AP-EVIDENCE — seeded leak must fail |
| 5 | **Tamper against us fails closed** (SC-41, blocking) | ▫ pending | FT-AP-TAMPER — every path denies + emits an event |
| 6 | **stdio MCP: authenticated call, 0 secret in config/env/context** (SC-12/13) | ▫ pending | FT-ST-*, FT-DK-BOUNDARY |
| 7 | **scan/migrate: 100% recall, 0 printed values** (SC-51, blocking) | ▫ pending | FT-MP-SCANMIGRATE |
| 8 | **Install → first brokered call < 15 min** (CUJ-1) | ▫ pending | FT-CL-FIRST — median of ≥5 fresh runs |
| 9 | **≥2 Tier-1 harness recipes end in a verified authenticated call** (E8) | ▫ pending | FT-HC-CLAUDE/CURSOR + honest not-yet (FT-HC-NOTYET) |
| 10 | **Offline: core + revoke with the network off** (CUJ-11, SC-39) | ▫ pending | FT-AG-OFFLINE, FT-DK-AIRGAP |
| 11 | **Conformance report green; unsupported standards labeled** (E13) | ▫ pending | FT-CONF-STANDARDS — DPoP `not-supported` |
| 12 | **Supply-chain floor** (E15, in-repo scope; signing/attestation = M15) | ▫ pending | FT-SC-INREPO, FT-DK-IMAGE |
| 13 | **Claims ≤ evidence labels; gaps named** (PRD 20 §6) | ▫ pending | FT-HONESTY-GAPS + the claims audit below |

---

## Small-Group Run Journal

Work is done in **small groups** (by pack). Each group: **run → ground → fix → journal**, then pause. A group
is listed here only once **every** case in it has run; any failing case is fixed before the group closes.
Grounding = the asserting check is re-derived from the committed results (`summary.json` assertions, ledger
rows, upstream captures), never trusted from the exit code; the leak scan (`evidence` scanner over the
results) must be clean.

> Template per group (duplicate per pack; delete this instruction block when the first real entry lands):
>
> ### Group N — `<pack>` — **X/X ✅ PASS, grounded** (date)
> - **Run:** `python scripts/fieldtest/run_pack.py --pack <pack>` → exit (fill); **X/X cases pass**.
> - **Grounding:** every PASS re-derived from the committed results; leak scan clean; (fill).
> - **Findings:** (fill: what the pack proved; defects found — none is an acceptable entry).
> - **What I fixed:** (fill: nothing, or the defect + its regression test).
> - **Working:** (fill: case ids). **Not working:** (fill: none, or case ids + why).
> - **Captured evidence:** `field-test/v0.1.0/results/<case-id>/…` (fill paths).

**Pack order (from the plan §7):** docker → core → binding → stdio → evasion → failclosed → audit → stepup →
attack → migrate → ops → nfr → conformance → killtime → contextdump → offline → harness.

---

## Environment

| Item | Value |
|---|---|
| Host | (fill: macOS/Linux, arch, CPU class) |
| Python | (fill) |
| Docker / Compose | (fill: version; image digests) |
| Broker image | (fill: `agentkeys-fieldtest:local` digest, base digest, non-root UID) |
| Compose file hash | (fill) |
| Git SHA under test | (fill) |
| Fake upstream / STS | (fill: versions/ports) |
| Tier-1 harnesses | (fill: Claude Code version, Cursor version — or "absent, WARN declared") |
| Results | `field-test/v0.1.0/results/<case-id>/` (summary.json, summary.md, env.json, commands.log) |
| Harness | `scripts/fieldtest/` (runner) + `python -m agentkeys.fieldtest` |

Recorded per run in `field-test/v0.1.0/results/<case-id>/env.json`. No secret values, ever.

---

## What Was Tested

**Harness + Docker topology (14.1) — (fill: done and exercised / not yet).**
- (fill: `scripts/fieldtest/run_pack.py` + `python -m agentkeys.fieldtest` + `cases.yaml`; compose
  topology: broker / child / upstream / airgap / scan services; per-run `env.json` fingerprint; the
  report-guard test.)

**Grounding — wired into the run, not a separate step.** (fill: how each PASS was re-derived; the leak gate
over the results; the falsification controls that fired.)

**Deterministic regression (Layer 0) — (fill).**
- (fill: full pytest suite result, conformance kit result, invariants I1–I10 result, attack-pack result at
  the field SHA.)

**Spot-verified cases.** (fill.)

**Not yet run (honest).** (fill: every pack/case without a verdict — stated as NOT RUN, never omitted.)

**WARN (honest).** (fill: each `P/F|W` case that warned, with its §8-plan limitation and the evidence of the
blocked attempt.)

---

## Scenario Results (Master Table)

74 field units ([plan §4](FIELD_TEST_PLAN.md) — 45 scenario/attack + 7 Docker + 7 ops + 10 NFR +
5 conformance/honesty). **Statuses are pending until a human enters them.**

### Blocking five (first; a red blocks M15)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-RK-KILLTIME | killtime (SC-24) | P/F | ▫ pending | p95 AND max ≤1s, N≥100/scope; replay provably refused |
| FT-AP-CONTEXTDUMP | contextdump (SC-40) | P/F | ▫ pending | 0 usable credentials; seeded control fires |
| FT-AP-TAMPER | attack (SC-41) | P/F | ▫ pending | every tamper path denies + emits an event |
| FT-AP-EVIDENCE | attack (SC-43) | P/F | ▫ pending | 0 secrets; seeded leak fails naming the row |
| FT-MP-SCANMIGRATE | migrate (SC-51) | P/F | ▫ pending | 100% recall; 0 printed values |

### Core lifecycle (SC-01–07)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-CL-FIRST | core (SC-01) | P/F\|W | ▫ pending | <15 min, ≥5 fresh runs |
| FT-CL-ENV | core (SC-02) | P/F | ▫ pending | |
| FT-CL-HEADER | core (SC-03) | P/F | ▫ pending | |
| FT-CL-EXCHANGE | core (SC-04) | P/F | ▫ pending | |
| FT-CL-TTL | core (SC-05) | P/F | ▫ pending | |
| FT-CL-ROTATE | core (SC-06) | P/F | ▫ pending | |
| FT-CL-TWOHARNESS | core (SC-07) | P/F | ▫ pending | |

### Binding / replay (SC-08–11)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-BR-AUDIENCE | binding (SC-08) | P/F | ▫ pending | |
| FT-BR-TOOL | binding (SC-09) | P/F | ▫ pending | |
| FT-BR-SESSION | binding (SC-10) | P/F | ▫ pending | |
| FT-BR-STALE | binding (SC-11) | P/F | ▫ pending | |

### stdio (SC-12–13)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-ST-NOSECRET | stdio (SC-12) | P/F | ▫ pending | container boundary + co-located limitation recorded |
| FT-ST-NOPASSTHRU | stdio (SC-13) | P/F | ▫ pending | |

### Evasion (SC-14–17)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-EV-DOTENV | evasion (SC-14) | P/F | ▫ pending | |
| FT-EV-CLOUD | evasion (SC-15) | P/F | ▫ pending | |
| FT-EV-KEYCHAIN | evasion (SC-16) | P/F | ▫ pending | |
| FT-EV-ENFORCE | evasion (SC-17) | P/F\|W | ▫ pending | gap named if no enforcer |

### Fail-closed (SC-18–23)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-FC-LOCKED | failclosed (SC-18) | P/F | ▫ pending | |
| FT-FC-ABSENT | failclosed (SC-19) | P/F | ▫ pending | |
| FT-FC-CONFIG | failclosed (SC-20) | P/F | ▫ pending | |
| FT-FC-STORE | failclosed (SC-21) | P/F | ▫ pending | |
| FT-FC-SINK | failclosed (SC-22) | P/F | ▫ pending | |
| FT-FC-CRASH | failclosed (SC-23) | P/F | ▫ pending | exactly-once asserted |

### Revocation / kill-time (SC-24–28)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-RK-SCOPE | killtime (SC-25) | P/F | ▫ pending | |
| FT-RK-INFLIGHT | killtime (SC-26) | P/F | ▫ pending | |
| FT-RK-UNKNOWN | killtime (SC-27) | P/F | ▫ pending | |
| FT-RK-ATTR | killtime (SC-28) | P/F | ▫ pending | |

### Lifecycle audit (SC-29–32)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-LA-EXPORT | audit (SC-29) | P/F | ▫ pending | two exports byte-identical |
| FT-LA-TAMPER | audit (SC-30) | P/F | ▫ pending | |
| FT-LA-NOSECRET | audit (SC-31) | P/F | ▫ pending | |
| FT-LA-EVENT | audit (SC-32) | P/F | ▫ pending | OTel GenAI shape |

### Step-up (SC-33–34)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-SU-APPROVED | stepup (SC-33) | P/F | ▫ pending | grant event after the mint, carries issuance_id |
| FT-SU-DENIED | stepup (SC-34) | P/F | ▫ pending | |

### Harness compatibility (SC-35–38)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-HC-CLAUDE | harness (SC-35) | P/F\|W | ▫ pending | tested version recorded |
| FT-HC-CURSOR | harness (SC-36) | P/F\|W | ▫ pending | |
| FT-HC-GENERIC | harness (SC-37) | P/F | ▫ pending | |
| FT-HC-NOTYET | harness (SC-38) | P/F | ▫ pending | |

### Air-gap (SC-39)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-AG-OFFLINE | offline (SC-39) | P/F | ▫ pending | |

### Attack packs (SC-40–43 + STRIDE DoS)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-AP-WIDEN | attack (SC-42) | P/F | ▫ pending | |
| FT-AP-FLOOD | attack (STRIDE DoS) | P/F | ▫ pending | fail closed under load |

### Migration (SC-51)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-MP-SCANMIGRATE | migrate (SC-51) | P/F | ▫ pending | (also in Blocking five) |

### Docker topology

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-DK-IMAGE | docker | P/F | ▫ pending | |
| FT-DK-COMPOSE | docker | P/F | ▫ pending | |
| FT-DK-QUICKSTART | docker | P/F | ▫ pending | |
| FT-DK-BOUNDARY | docker | P/F | ▫ pending | |
| FT-DK-AIRGAP | docker | P/F | ▫ pending | |
| FT-DK-EVIDENCE | docker | P/F | ▫ pending | |
| FT-DK-SINGLEWRITER | docker | P/F | ▫ pending | |

### Operations

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-OPS-SERVE | ops | P/F | ▫ pending | |
| FT-OPS-BACKUP | ops | P/F | ▫ pending | |
| FT-OPS-RESTORE | ops | P/F | ▫ pending | |
| FT-OPS-MIGRATE | ops | P/F | ▫ pending | |
| FT-OPS-DOCTOR | ops | P/F | ▫ pending | <2s |
| FT-OPS-DRILL | ops | P/F | ▫ pending | |
| FT-OPS-RETENTION | ops | P/F | ▫ pending | |

### NFRs

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-NFR-INJECT | nfr | P/F | ▫ pending | measured p99 recorded |
| FT-NFR-BACKEND | nfr | P/F | ▫ pending | |
| FT-NFR-THROUGHPUT | nfr | P/F | ▫ pending | ≥100 issuances/s |
| FT-NFR-COLDSTART | nfr | P/F | ▫ pending | |
| FT-NFR-RESTART | nfr | P/F | ▫ pending | <1s |
| FT-NFR-LEDGER | nfr | P/F | ▫ pending | |
| FT-NFR-RSS | nfr | P/F | ▫ pending | |
| FT-NFR-CLOCK | nfr | P/F | ▫ pending | |
| FT-NFR-PORT | nfr | P/F | ▫ pending | |
| FT-NFR-A11Y | nfr | P/F | ▫ pending | |

### Conformance, supply chain, honesty

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-CONF-STANDARDS | conformance | P/F | ▫ pending | DPoP `not-supported` |
| FT-CONF-BACKENDS | conformance | P/F | ▫ pending | |
| FT-SC-INREPO | conformance | P/F | ▫ pending | signing = M15 |
| FT-HONESTY-GAPS | conformance | P/F | ▫ pending | |
| FT-HONESTY-REPORT | conformance | P/F | ▫ pending | guard refuses this file |

**Totals:** 0 ✅ PASS · 0 ❌ FAIL · 0 ⚠ WARN · 74 ▫ NOT RUN — *(fill final totals by hand when the sweep
completes)*.

---

## Per-Pack Results

| Pack | Cases | PASS | FAIL | WARN | NOT RUN |
|---|---|---|---|---|---|
| docker | 7 | 0 | 0 | 0 | 7 |
| core | 7 | 0 | 0 | 0 | 7 |
| binding | 4 | 0 | 0 | 0 | 4 |
| stdio | 2 | 0 | 0 | 0 | 2 |
| evasion | 4 | 0 | 0 | 0 | 4 |
| failclosed | 6 | 0 | 0 | 0 | 6 |
| killtime | 5 | 0 | 0 | 0 | 5 |
| audit | 4 | 0 | 0 | 0 | 4 |
| stepup | 2 | 0 | 0 | 0 | 2 |
| harness | 4 | 0 | 0 | 0 | 4 |
| offline | 1 | 0 | 0 | 0 | 1 |
| attack | 4 | 0 | 0 | 0 | 4 |
| migrate | 1 | 0 | 0 | 0 | 1 |
| ops | 7 | 0 | 0 | 0 | 7 |
| nfr | 10 | 0 | 0 | 0 | 10 |
| conformance | 5 | 0 | 0 | 0 | 5 |
| **Total** | **74** | **0** | **0** | **0** | **74** |

*(FT-MP-SCANMIGRATE counts once, in migrate; FT-RK-KILLTIME once, in killtime. Update by hand.)*

---

## Root Cause Analysis

> Template per failure (duplicate per FAIL; delete this instruction block when the first entry lands):
>
> ### `<case-id>` — FAIL (fixed / open) — one-line root cause
> - **Symptom:** (fill: what the result showed, with the numbers.)
> - **Root cause:** (fill: the actual cause — product or harness; say which.)
> - **Fix:** (fill: the change + its regression test.)
> - **Verification:** (fill: the re-run result — re-run only the affected pack.)

---

## Defect Catalogue

| # | Defect | Found by | Fix | Regression evidence |
|---|---|---|---|---|
| (fill) | | | | |

---

## Field Notes — Findings, Learnings, and Observations

Detailed notes from the run, for the write-ups. Each is a claim **grounded in the evidence paths cited**.
Themes worth capturing (from the plan and PRDs — fill with what actually happens):

1. **The verdict vocabulary is the product** — WARN with a named limitation ≠ PASS; NOT RUN ≠ omitted
   ([PRD 17 §16](../../prd/17-scenarios.md)).
2. **"Exit 0" is not "the test passed"** — grounding re-derivation, and the falsification controls that
   prove the scanner can fail.
3. **The Docker boundary is the flagship's honesty** — what FT-DK-BOUNDARY proved about the co-located
   limitation ([PRD 06 §4](../../prd/06-security-baseline.md)).
4. **The kill-time number** — p50/p95/max, the machine class, and what the replay proof actually showed.
5. **Zero printed values** — how the never-print rule was verified (string search over every artifact).
6. **Small groups beat one big sweep** — interrupted runs, per-pack commits, cheap restarts.
7. **Environment facts that mattered** — reproducibility notes (image digests, versions, quirks).
8. **Honest remaining work** — anything open at the time of writing, struck through when closed.

---

## Coverage, Gaps, and Declared Limitations

Status vocabulary: **NOT RUN | PASS | FAIL | WARN | N/A** — this run so far: **0 PASS · 0 FAIL · 0 WARN ·
74 NOT RUN**.

- **Coverage so far:** (fill: which packs ran; which plan §5 coverage rows are satisfied by a verdict.)
- **Failing:** (fill: none, or each FAIL with its RCA section.)
- **WARN:** (fill: each with its §8-plan limitation + the evidence of the blocked attempt. The four
  `P/F|W` candidates: FT-CL-FIRST, FT-EV-ENFORCE, FT-HC-CLAUDE, FT-HC-CURSOR.)
- **Removed from scope:** (fill: any case dropped — with the reason and where it is documented as
  not-supported. Never a silent drop.)
- **NOT RUN:** (fill: every case without a verdict — stated, never omitted. A NOT RUN on a blocking case
  keeps M15 blocked.)
- **Not tested (honest):** everything not listed as PASS/FAIL/WARN above — stated as NOT RUN.

### Claims-label audit ([PRD 20 §6](../../prd/20-standards-and-claims.md))

Every public claim promoted by this run, with its label and the row that earned it:

| Claim | Label earned | Evidence row |
|---|---|---|
| (fill: e.g. "revoke ≤1s, replay-verified") | field-tested | FT-RK-KILLTIME |
| (fill) | | |

No claim above its evidence; nothing is *verified* until a third party re-runs `bench/`.

---

## Success Metrics ([PRD 07](../../prd/07-success-metrics.md); Achieved filled as the sweep runs)

| Measure | Target | Achieved | Evidence |
|---|---|---|---|
| Kill-time end-to-end | p95 ≤1s AND max ≤1s, N≥100/scope | ▫ | FT-RK-KILLTIME |
| Zero usable credentials | exactly 0, every variant | ▫ | FT-AP-CONTEXTDUMP |
| Zero secrets in store/export/ledger | exactly 0 | ▫ | FT-AP-EVIDENCE |
| Time-to-first-brokered-call | <15 min median, ≥5 runs | ▫ | FT-CL-FIRST |
| Step-up no-widening | 100% | ▫ | FT-SU-*, FT-AP-WIDEN |
| Tier-1 harnesses covered | ≥2 with green recipes | ▫ | FT-HC-CLAUDE/CURSOR |
| Evasion pack caught | 100% of the pack; gaps named | ▫ | FT-EV-* |
| Passthrough rejected | 100% of fixtures | ▫ | FT-ST-NOPASSTHRU, FT-CL-HEADER |
| Fail-closed matrix | 100% deny-or-pending | ▫ | FT-FC-* |
| Scan recall / printed values | 100% recall; 0 printed | ▫ | FT-MP-SCANMIGRATE |

---

## Performance & Timings

Measured numbers with their machine class (from `env.json`) — never a fleet claim; a missed target is a
finding, not a rounding.

| Measure | Value | Machine class |
|---|---|---|
| Kill-time p50 / p95 / max (per scope) | (fill) | (fill) |
| Egress injection p99 (env / header / exchange) | (fill) | (fill) |
| Backend resolution p99 (file / keychain) | (fill) | (fill) |
| Issuance throughput | (fill) | (fill) |
| Broker cold start / restart-to-serving | (fill) | (fill) |
| Ledger append p99 | (fill) | (fill) |
| Idle RSS (container) | (fill) | (fill) |
| `doctor` runtime | (fill) | (fill) |
| Docker image build / stack readiness | (fill) | (fill) |

---

## Action Items

Done:
1. [ ] (fill: harness + Docker topology built and exercised.)
2. [ ] (fill: grounding + leak gates wired into the runner.)
3. [ ] (fill: report guard shipped with the writer.)

Next:
4. [ ] (fill: packs remaining, in plan §7 order.)
5. [ ] (fill: open defects and their fixes.)
6. [ ] (fill: M15 hand-off — audit, claims lint, matrix, signing, tag — only after the blocking five PASS.)
7. [ ] Keep updating **this report by hand** with any re-run verdicts + learnings.

---

## Reproducibility / Evidence Paths

```sh
# Environment + harness
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml up -d broker child upstream

# Packs (results -> field-test/v0.1.0/results/<case-id>/)
python scripts/fieldtest/run_pack.py --pack docker
python scripts/fieldtest/run_pack.py --pack core        # …one pack at a time, plan §7 order

# The blocking measurements (published copies -> bench/)
python -m agentkeys.bench.killtime --iterations 100
python scripts/fieldtest/run_pack.py --pack killtime
python scripts/fieldtest/run_pack.py --pack contextdump

# Gates (also run inside the runner)
.venv/bin/python -m pytest
.venv/bin/python -m agentkeys conformance --json
```

**This report is hand-maintained.** The runner refuses any output path under `docs/field-test/` or matching a
`HAND-MAINTAINED` file; automated drafts write `FIELD_TEST_REPORT.generated.md` only. The guard is
`tests/test_field_report_guard.py`.

## Appendices

- Plan: [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) (matrix §4, coverage §5, blocking specs §6, gates §9).
- WBS: [Part 8](../../wbs/v0.1.0/wbs-v0.1.0-part8-fieldtest-release.md) (M14).
- PRDs: [04 users/CUJs](../../prd/04-users-and-cujs.md) · [05 features](../../prd/05-features.md) ·
  [06 security baseline](../../prd/06-security-baseline.md) · [07 success metrics](../../prd/07-success-metrics.md) ·
  [17 scenarios](../../prd/17-scenarios.md) · [20 standards & claims](../../prd/20-standards-and-claims.md) ·
  [21 evidence & method](../../prd/21-evidence-register-and-method.md).
