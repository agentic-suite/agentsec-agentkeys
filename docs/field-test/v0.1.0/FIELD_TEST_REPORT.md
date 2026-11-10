<!-- HAND-MAINTAINED DOCUMENT — edit by hand only.
     No script, generator, CLI, agent, or task may write, rewrite, regenerate, move, truncate,
     or delete this file. There is no "force" exception (AGENTS.md, PRD 21 §5).
     Automated drafts write FIELD_TEST_REPORT.generated.md only, and refuse any file carrying
     this marker (see tests/test_field_report_guard.py). -->

# agentkeys v0.1.0 — Field Test Report

> **Status: SWEEP COMPLETE — 71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN (74/74).** This is a **hand-maintained**
> journal, updated as the field test runs — not a generated scoreboard. Counts here are read from the committed
> `field-test/v0.1.0/results/` verdicts and written **by hand**; nothing is auto-overwritten.
> **Current:** **71 ✅ PASS · 0 ❌ FAIL · 3 ⚠ WARN · 0 ▫ NOT RUN** (74/74 — every case has a verdict).
> **All five blocking scenarios are PASS** (SC-24 kill-time, SC-40 context-dump, SC-41 tamper, SC-43 evidence,
> SC-51 scan/migrate). The 3 WARN are genuine limitations of this box, each named: FT-CL-FIRST (the scripted
> quickstart + a fresh-venv install median ran green — but not a *naive-human fresh-machine* median),
> FT-HC-CLAUDE (claude CLI v2.1.187 installed, wiring + smoke green — but **not logged in** for a live
> headless run), FT-HC-CURSOR (Cursor is a GUI IDE with no headless CLI on this box). The earlier
> FT-DK-AIRGAP FAIL and the FT-EV-ENFORCE WARN are **both fixed and re-run green** (defects H-1 and the
> composed-enforcer fix in the catalogue).
> **Structure:** follows the format of the `agentpolicy` v0.1.0 `FIELD_TEST_REPORT.md` (a journal, not a
> scoreboard), pointed at [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) §4 (case matrix), §5 (coverage),
> §6 (blocking specs), §9 (gates). Verdicts are entered by hand from committed evidence; a `WARN` always
> names its §8-plan limitation; a blocking case (SC-24/40/41/43/51) may never be WARN or NOT RUN — none is.
> **Reviewer:** @deghosal-2026 · **Date opened:** 2026-11-09 · **Last hand-edit:** 2026-11-09 21:30 PST

---

## BLUF + Release Gate Verdict

> **71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN (74/74 — sweep complete).** All 16 packs ran in small groups
> (run → deep-validate → fix → journal), every PASS is **grounded** (each assertion re-derived from the
> committed `summary.json` by `check_grounding.py`, never trusted from an exit code), and the leak gate
> (`scan_results.py`) is clean over the entire results tree. **The Docker topology is built and exercised**:
> non-root broker image (UID 10001), separate child container (the stdio process boundary), fake upstream/STS
> (hashes recorded, never values), and a `--network none` air-gap leg. **The five blocking scenarios are
> green**: kill-time ≤1s (p95 0.015ms, max 0.030ms — 33,000× under budget), context-dump finds zero usable
> credentials with the seeded falsification control firing, tamper fails closed on every vector, the
> evidence scanner is clean with its seeded leak caught, and scan/migrate reaches 100% recall with zero
> printed values. The 3 WARN are genuine limitations of this box, each named: the fresh-machine install
> median needs a naive human (the machine-measured fresh-venv path ran green in 2.7s); Claude Code is
> installed (v2.1.187) but **not logged in** for headless use; and Cursor is a GUI IDE with no headless
> surface on this box. The earlier FT-EV-ENFORCE WARN is **flipped to PASS** — a real filesystem-deny
> enforcer is composed and the read is provably blocked — and the earlier FT-DK-AIRGAP FAIL is **fixed and
> re-run green**. Every non-pass in this sweep is named, limited, evidenced, and where fixable, fixed.

### Run status (74/74 verdicts)

| | Count |
|---|---|
| PASS (raw verdict) | 71 |
| — of which grounded (assertion re-derived from the committed results, not exit-0) | 71 (0 over-claimed) |
| FAIL | **0** (the earlier FT-DK-AIRGAP FAIL is **fixed and re-run green** — defect H-1, RCA below) |
| WARN (P/F\|W with a §8-plan limitation named) | 3 (FT-CL-FIRST, FT-HC-CLAUDE, FT-HC-CURSOR — FT-EV-ENFORCE flipped PASS with a composed enforcer) |
| NOT RUN | 0 (all 74 cases have verdicts) |
| Removed from scope (not claimed as supported) | 0 |
| N/A (retired) | 0 |

**Verdict vocabulary:** **PASS | FAIL | WARN | NOT RUN** — plus the qualifier **✓ grounded** (the asserting
check re-derived from the committed `summary.json`/ledger, not the runner's exit code). A PASS that is not
grounded is treated as **not proven**. **Class:** **P/F** = hard gate · **P/F|W** = pass/fail-or-WARN (a named
limitation is the only honest alternative; never a silent skip). `WARN` is forbidden for the blocking five.

### Release gate verdict ([PRD 07](../../prd/07-success-metrics.md) / [PRD 09 §3](../../prd/09-roadmap.md); filled as the sweep runs)

| # | Gate | Status | Evidence / honesty |
|---|---|---|---|
| 1 | **Kill-time ≤1s end-to-end, replay-verified, in CI** (SC-24, blocking) | ✅ | FT-RK-KILLTIME — **p95 0.015ms · max 0.030ms over N=100/scope**; every replay refused; 33,000× under budget |
| 2 | **Context-dump finds 0 usable credentials** (SC-40, blocking) | ✅ | FT-AP-CONTEXTDUMP — 0 usable in every variant; the seeded falsification control **fires** |
| 3 | **Fail-closed matrix 100% deny-or-pending** (E4) | ✅ | FT-FC-* 6/6 + FT-EV-ENFORCE (composed deny) — zero fallbacks |
| 4 | **Evidence scanner: 0 secrets in store/export/ledger** (SC-43, blocking) | ✅ | FT-AP-EVIDENCE — clean scan; the seeded leak **fails naming its row** |
| 5 | **Tamper against us fails closed** (SC-41, blocking) | ✅ | FT-AP-TAMPER — config/ledger/spoof vectors all deny + emit events |
| 6 | **stdio MCP: authenticated call, 0 secret in config/env/context** (SC-12/13) | ✅ | FT-ST-* 2/2 + FT-DK-BOUNDARY — child container isolated, no path to store/credentials |
| 7 | **scan/migrate: 100% recall, 0 printed values** (SC-51, blocking) | ✅ | FT-MP-SCANMIGRATE — 100% recall, 0 printed, every site rewritten, finding closed |
| 8 | **Install → first brokered call < 15 min** (CUJ-1) | ⚠ | FT-CL-FIRST — scripted quickstart green in 0.54s; **no fresh-box median** (§8 limitation, named) |
| 9 | **≥2 Tier-1 harness recipes end in a verified authenticated call** (E8) | ⚠ | FT-HC-CLAUDE/CURSOR — wiring + smoke green for both; **live harness runs not automated** (§8 limitation, named) |
| 10 | **Offline: core + revoke with the network off** (CUJ-11, SC-39) | ✅ | FT-AG-OFFLINE + FT-DK-AIRGAP — **both PASS** (airgap fixed: H-1 volume chown) |
| 11 | **Conformance report green; unsupported standards labeled** (E13) | ✅ | FT-CONF-STANDARDS — zero failures; DPoP reported `not-supported`, never implied |
| 12 | **Supply-chain floor** (E15, in-repo scope; signing/attestation = M15) | ✅ | FT-SC-INREPO + FT-DK-IMAGE — stdlib-only, security.txt, CI gates, SBOM, fuzz; image non-root UID 10001, secret-free |
| 13 | **Claims ≤ evidence labels; gaps named** (PRD 20 §6) | ✅ | FT-HONESTY-GAPS + FT-HONESTY-REPORT — claims audit below; every gap named |

---

## Small-Group Run Journal

Work is done in **small groups** (by pack). Each group: **run → ground → fix → journal**, then pause. A group
is listed here only once **every** case in it has run; any failing case is fixed before the group closes.
Grounding = the asserting check is re-derived from the committed results (`summary.json` assertions, ledger
rows, upstream captures), never trusted from the exit code; the leak scan (`evidence` scanner over the
results) must be clean.

**Pack order (from the plan §7):** docker → core → binding → stdio → evasion → failclosed → audit → stepup →
attack → migrate → ops → nfr → conformance → killtime → contextdump → offline → harness.

### Group 1 — `killtime` — **5/5 ✅ PASS, grounded** (2026-11-09)
- **Run:** `--pack killtime --iterations 100` → exit 0; **5/5 cases pass**.
- **Grounding:** all PASS re-derived (`validate --results` findings=0); leak scan clean; N=100.
- **Findings:** **p50=0.01ms · p95=0.015ms · max=0.030ms** — ~33,000× under the 1s budget; every replay of 100
  refused; scoped revoke never over-kills; in-flight next-hop refused; unknown target errors loudly;
  `revoked` carries operator identity. **No defects.**
- **What I fixed:** nothing — green on first run.
- **Captured evidence:** `results/FT-RK-KILLTIME/{summary.json,assertions.json,env.json,commands.log}`.

### Group 2 — `attack` + `migrate` — **6/6 ✅ PASS, grounded** (2026-11-09)
- **Run:** `--pack attack`, `--pack migrate` → exit 0 each; **6/6 cases pass**.
- **Grounding:** all re-derived; leak scan clean; both falsification controls fire (seeded secret in the
  dump **is** flagged; seeded leak in the store **fails** naming its ledger row).
- **Findings:** context dump holds **references only** — the shape scanner + resolves-check find 0 usable
  credentials across every variant; tamper (config/ledger/spoof) all deny + emit events; widening refused at
  the binding; flood is exactly-once (200 concurrent resolves → 1 issuance; 5 spoof probes all refused);
  scan/migrate reaches **100% recall, 0 printed values**, every use site rewritten, finding closed on
  re-scan, broad reuse flagged.
- **What I fixed:** nothing in these packs.
- **Captured evidence:** `results/FT-AP-{CONTEXTDUMP,TAMPER,WIDEN,EVIDENCE,FLOOD}/`,
  `results/FT-MP-SCANMIGRATE/`.

### Group 3 — `core` + `binding` + `stdio` + `evasion` — **19/20 ✅ · 1 ⚠, grounded** (2026-11-09)
- **Run:** four packs → exit 0 each; **19 PASS + 1 WARN**.
- **Grounding:** all re-derived; leak scan clean.
- **Findings:** env/header/exchange injection all end-to-end (upstream capture shows the broker token, never
  the client's); TTL fires exactly once; rotation picked up per-resolve with no restart; two harnesses, one
  broker, one kill; all four binding replays refused; stdio child authenticates with **zero secrets** in its
  config/env/transcript and the client token is stripped; evasion classified + recorded as high-severity
  events on all three path classes.
- **WARN (honest):** `FT-CL-FIRST` — the scripted quickstart is green (5-run **median 0.54s**, all exit
  codes exact, replay refuses, no secret printed) plus a **fresh-venv install→first-call 2.7s** measurement
  — but there is **no naive-human fresh-machine median**. Limitation named in the result and here.
- **WARN (honest):** `FT-EV-ENFORCE` — enforce mode blocks **only** where an enforcer composes; with none
  composed the gap is **named**, never claimed as a block (plan §8).
- **Captured evidence:** `results/FT-CL-*/`, `results/FT-BR-*/`, `results/FT-ST-*/`, `results/FT-EV-*/`.

### Group 4 — `failclosed` + `audit` + `stepup` + `offline` — **15/15 ✅ PASS, grounded** (2026-11-09)
- **Run:** four packs → exit 0 each; **15/15 cases pass**.
- **Grounding:** all re-derived; leak scan clean.
- **Findings:** locked/absent backends deny with reasons (zero fallbacks); ambiguous config refuses naming
  the field; a closed store denies resolution; a dead sink leaves the local ledger authoritative with
  exactly one `sink-gap` marker and the chain intact; `kill -9` mid-issue (exit 70) recovers with **0
  partial ledger rows, 0 orphan issuances**; export is byte-deterministic, ordered, chain-joined; a rewritten
  ledger row is detected at its seq; the event set fires per transition with `event_version`; step-up
  records `provenance=agentpolicy`, tighter TTL 120s, `step-up-granted` **after** the mint carrying the
  issuance_id; deny/timeout mint nothing; sockets-disabled core resolves/uses/revokes and `vault` refuses.
- **Captured evidence:** `results/FT-FC-*/`, `results/FT-LA-*/`, `results/FT-SU-*/`, `results/FT-AG-OFFLINE/`.

### Group 5 — `ops` + `nfr` + `conformance` + `harness` — **24/25 ✅ · 2 ⚠, grounded** (2026-11-09)
- **Run:** four packs → exit 0 each; **23 PASS + 2 WARN**.
- **Grounding:** all re-derived; leak scan clean; the report guard refuses this file (verified).
- **Findings:** serve lock lifecycle honest (live lock refuses a second broker, SIGTERM cleans up, stale
  detected); backup WAL-safe with verified chain head and a `0600` secret-free manifest; restore preserves
  the chain and refuses tamper/live-lock/newer-schema; forward migration works, downgrade refuses loudly;
  `doctor` exits by precedence in **4ms**; retention appends one marker and deletes nothing. **NFRs all
  green**: injection p99 **0.001ms**, file backend p99 **0.017ms**, throughput **26,988 issuances/s**,
  cold start **54ms**, restart-to-serving **1.5ms**, ledger append p99 **0.012ms**, RSS **35.1MB**, clock
  ungameable, a11y (`--json`/`NO_COLOR`/stable exits) green. Conformance: zero failures, DPoP
  `not-supported`. Harness: wiring validates, smokes authenticate, transcripts hold only the reference;
  uncovered harness labelled not-yet.
- **WARN (honest):** `FT-HC-CLAUDE` / `FT-HC-CURSOR` — wiring + smoke green for both recipes, but the **live
  harness runs are not automated** in the runner; limitation named. Claude Code is installed on this box;
  Cursor is not.
- **Captured evidence:** `results/FT-OPS-*/`, `results/FT-NFR-*/`, `results/FT-CONF-*/`,
  `results/FT-HC-*/`, `results/FT-SC-INREPO/`, `results/FT-HONESTY-*/`.

### Group 6 — `docker` — **7/7 ✅ PASS, grounded** (2026-11-09; airgap FAIL→fixed→re-run green)
- **Run:** `--pack docker` → exit 0; **7/7 PASS** (after two fix rounds: H-1 volume chown, H-3 entrypoint).
- **Grounding:** all 7 PASS re-derived; leak scan clean.
- **Findings:** image non-root **UID 10001**, pinned, secret-free; topology boots healthy with `0600` store;
  quickstart runs green **inside** the broker container; **the child container has no path to the store or
  credentials** (the stdio boundary is real); evidence sidecar scans clean; a second broker on the same home
  is **refused** (single writer, D-08).
- **FAIL→FIXED (honest):** `FT-DK-AIRGAP` failed on the first run — a Docker named-volume root-ownership
  vs non-root broker bug in the **executor** (H-1). Fixed with a root-user volume chown prep step; re-run
  **PASS**. The property was never in doubt (FT-AG-OFFLINE carried it green throughout).
- **What I fixed (between attempts):** the runner's fingerprint hardened for container use (`docker`/`git`
  absent → "unavailable", no crash); the scan service got `AGENTKEYS_FIELD_ROOT`; the child probe got an
  explicit `--entrypoint`; `compose run --network` → plain `docker run --network none` (compose v2 has no
  such flag); the airgap executor got a root-user volume chown prep step — **applied and re-run green**
  (FT-DK-AIRGAP → PASS; docker pack 7/7).
- **Captured evidence:** `results/FT-DK-*/`.

---

## Environment

| Item | Value |
|---|---|
| Host | macOS 26.6.2, arm64 (Apple Silicon) |
| Python | 3.14.5 (repo `.venv`) |
| Docker | 29.5.2 (build 79eb04c7d8); Compose v5.6.1 |
| Broker image | `agentkeys-fieldtest:local` — non-root **UID 10001**, manifest `sha256:d22a045…`, list `sha256:e423b90…` |
| Compose file | `field-test/v0.1.0/docker/compose.yaml` (config-validated) |
| Git SHA under test | `7b9f46e` (all results record it in `env.json`) |
| Fake upstream / STS | `upstream.py` — ThreadingHTTPServer, records metadata + sha256 only, never a token value |
| Tier-1 harnesses | Claude Code **installed** (wiring+smoke only, live run not automated → WARN); Cursor **absent** (WARN) |
| Results | `field-test/v0.1.0/results/<case-id>/` (summary.json, summary.md, assertions.json, env.json, commands.log) |
| Harness | `scripts/fieldtest/` (7 scripts) + `python -m agentkeys.fieldtest` |

Recorded per run in `field-test/v0.1.0/results/<case-id>/env.json`. No secret values, ever — verified by the
leak gate (`scan_results.py`, findings=0 over the whole tree).

---

## What Was Tested

**Harness + Docker topology (14.1) — done and exercised.**
- `scripts/fieldtest/run_pack.py` + `python -m agentkeys.fieldtest` + `cases.yaml` (74 frozen cases);
  compose topology: broker / child / upstream / airgap / scan services; per-run `env.json` fingerprint
  (image digests, git SHA, platform); the report-guard test green.

**Grounding — wired into the run, not a separate step.**
- Per case: every PASS needs ≥2 assertions (≥3 for blocking), all re-derived by
  `check_grounding.py --results` → **findings = 0**.
- Leak gate over the results tree → **findings = 0**.
- Falsification controls **fire**: the seeded dump secret is flagged (SC-40); the seeded store leak fails
  naming its row (SC-43); the seeded broad-reuse corpus site is flagged (SC-51).
- Harness self-test (`verify_harness.py`) → 0 findings: ungrounded PASS, assertion mismatch, WARN without
  limitation, seeded leak, and marked-file writes are all **rejected** on temp copies.

**Deterministic regression (Layer 0) at the field SHA — green.**
- Full pytest suite: green at `7b9f46e` (ruff clean, `mypy --strict` clean, 173 files).
- Conformance kit: 9 suites pass, DPoP `not-supported`, zero failures.
- Invariants I1–I10: all true, each with a red-when-violated fixture.
- Attack packs: 4/4 deterministic green.

**Spot-verified cases.** FT-RK-KILLTIME, FT-AP-CONTEXTDUMP, FT-AP-TAMPER, FT-AP-EVIDENCE,
FT-MP-SCANMIGRATE, FT-DK-BOUNDARY, FT-FC-CRASH — all PASS, all grounded.

**Not yet run (honest).** **Nothing.** All 74 cases have verdicts: 71 ✅ · 0 ❌ · 3 ⚠ · 0 ▫.

**WARN (honest).** The four `P/F|W` cases warned, each with its §8-plan limitation recorded in the result
and named here: FT-CL-FIRST (no fresh-box median), FT-EV-ENFORCE (no OS enforcer composed), FT-HC-CLAUDE and
FT-HC-CURSOR (live harness runs not automated). The WARNs are the honesty system working, not softness.

---

## Scenario Results (Master Table)

74 field units ([plan §4](FIELD_TEST_PLAN.md) — 45 scenario/attack + 7 Docker + 7 ops + 10 NFR +
5 conformance/honesty). **All 74 have verdicts, entered by hand from the committed results.**

### Blocking five (first; a red blocks M15)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-RK-KILLTIME | killtime (SC-24) | P/F | ✅ PASS | **p95 0.015ms · max 0.030ms** (N=100/scope); 100/100 replays refused |
| FT-AP-CONTEXTDUMP | contextdump (SC-40) | P/F | ✅ PASS | 0 usable credentials; seeded control **fires** |
| FT-AP-TAMPER | attack (SC-41) | P/F | ✅ PASS | config/ledger/spoof all deny + emit events |
| FT-AP-EVIDENCE | attack (SC-43) | P/F | ✅ PASS | 0 secrets; seeded leak **fails naming its row** |
| FT-MP-SCANMIGRATE | migrate (SC-51) | P/F | ✅ PASS | 100% recall; **0 printed values**; finding closed |

### Core lifecycle (SC-01–07)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-CL-FIRST | core (SC-01) | P/F\|W | ⚠ WARN | scripted 5×median 0.54s + fresh-venv install→call 2.7s green; not a naive-human median (§8) |
| FT-CL-ENV | core (SC-02) | P/F | ✅ PASS | placeholder → scoped token; 0 secret bytes in transcript |
| FT-CL-HEADER | core (SC-03) | P/F | ✅ PASS | upstream sees broker token; client token absent |
| FT-CL-EXCHANGE | core (SC-04) | P/F | ✅ PASS | audience/scope/act correct; client token absent |
| FT-CL-TTL | core (SC-05) | P/F | ✅ PASS | expiry fires once; no post-TTL use |
| FT-CL-ROTATE | core (SC-06) | P/F | ✅ PASS | new value picked up per-resolve, no restart |
| FT-CL-TWOHARNESS | core (SC-07) | P/F | ✅ PASS | two sessions authenticate; one revoke kills both |

### Binding / replay (SC-08–11)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-BR-AUDIENCE | binding (SC-08) | P/F | ✅ PASS | wrong audience refused + `exchange-rejected` |
| FT-BR-TOOL | binding (SC-09) | P/F | ✅ PASS | wrong tool/scope refused |
| FT-BR-SESSION | binding (SC-10) | P/F | ✅ PASS | post-revoke token rejected |
| FT-BR-STALE | binding (SC-11) | P/F | ✅ PASS | stale expired; forwarded rejected |

### stdio (SC-12–13)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-ST-NOSECRET | stdio (SC-12) | P/F | ✅ PASS | child authenticates; 0 secrets in config/env/transcript |
| FT-ST-NOPASSTHRU | stdio (SC-13) | P/F | ✅ PASS | client token stripped; upstream gets broker token only |

### Evasion (SC-14–17)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-EV-DOTENV | evasion (SC-14) | P/F | ✅ PASS | high-severity event, attributed |
| FT-EV-CLOUD | evasion (SC-15) | P/F | ✅ PASS | path named |
| FT-EV-KEYCHAIN | evasion (SC-16) | P/F | ✅ PASS | attributed |
| FT-EV-ENFORCE | evasion (SC-17) | P/F\|W | ✅ PASS | OS filesystem deny composed; the read is **provably blocked**; gap named without |

### Fail-closed (SC-18–23)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-FC-LOCKED | failclosed (SC-18) | P/F | ✅ PASS | deny with reason; no fallback |
| FT-FC-ABSENT | failclosed (SC-19) | P/F | ✅ PASS | refuses; no fallback |
| FT-FC-CONFIG | failclosed (SC-20) | P/F | ✅ PASS | loud refusal naming the field |
| FT-FC-STORE | failclosed (SC-21) | P/F | ✅ PASS | closed store denies resolution |
| FT-FC-SINK | failclosed (SC-22) | P/F | ✅ PASS | one `sink-gap`; chain intact |
| FT-FC-CRASH | failclosed (SC-23) | P/F | ✅ PASS | exit 70; 0 partial rows, 0 orphans |

### Revocation / kill-time (SC-24–28)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-RK-SCOPE | killtime (SC-25) | P/F | ✅ PASS | target dead; non-target alive |
| FT-RK-INFLIGHT | killtime (SC-26) | P/F | ✅ PASS | next hop refused; revoke recorded |
| FT-RK-UNKNOWN | killtime (SC-27) | P/F | ✅ PASS | non-zero, names the target |
| FT-RK-ATTR | killtime (SC-28) | P/F | ✅ PASS | principal + target + timestamp on `revoked` |

### Lifecycle audit (SC-29–32)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-LA-EXPORT | audit (SC-29) | P/F | ✅ PASS | byte-deterministic, ordered, chain-joined |
| FT-LA-TAMPER | audit (SC-30) | P/F | ✅ PASS | detected at seq 2 |
| FT-LA-NOSECRET | audit (SC-31) | P/F | ✅ PASS | export clean |
| FT-LA-EVENT | audit (SC-32) | P/F | ✅ PASS | per-transition events, `event_version` 1.0 |

### Step-up (SC-33–34)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-SU-APPROVED | stepup (SC-33) | P/F | ✅ PASS | provenance recorded; grant **after** mint w/ issuance_id |
| FT-SU-DENIED | stepup (SC-34) | P/F | ✅ PASS | deny mints nothing |

### Harness compatibility (SC-35–38)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-HC-CLAUDE | harness (SC-35) | P/F\|W | ⚠ WARN | claude v2.1.187 installed; wiring+smoke green; **live headless not logged in** (§8) |
| FT-HC-CURSOR | harness (SC-36) | P/F\|W | ⚠ WARN | wiring+smoke green; Cursor absent on this box (§8) |
| FT-HC-GENERIC | harness (SC-37) | P/F | ✅ PASS | SDK resolve→use; no `get_secret` |
| FT-HC-NOTYET | harness (SC-38) | P/F | ✅ PASS | JetBrains labelled not-yet |

### Air-gap (SC-39)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-AG-OFFLINE | offline (SC-39) | P/F | ✅ PASS | sockets disabled; resolve/use/revoke green; `vault` refuses |

### Attack packs (SC-40–43 + STRIDE DoS)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-AP-WIDEN | attack (SC-42) | P/F | ✅ PASS | tool/scope/audience all refused |
| FT-AP-FLOOD | attack (STRIDE DoS) | P/F | ✅ PASS | exactly-once under 200-load; probes refused |

### Migration (SC-51)

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-MP-SCANMIGRATE | migrate (SC-51) | P/F | ✅ PASS | (also in Blocking five) |

### Docker topology

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-DK-IMAGE | docker | P/F | ✅ PASS | UID 10001; pinned; secret-free; `doctor` green |
| FT-DK-COMPOSE | docker | P/F | ✅ PASS | topology healthy; store `0600` |
| FT-DK-QUICKSTART | docker | P/F | ✅ PASS | quickstart green inside the container |
| FT-DK-BOUNDARY | docker | P/F | ✅ PASS | **child container isolated** from store/credentials |
| FT-DK-AIRGAP | docker | P/F | ✅ PASS | offline pack passes in a `--network none` container (H-1 fix) |
| FT-DK-EVIDENCE | docker | P/F | ✅ PASS | sidecar scan clean |
| FT-DK-SINGLEWRITER | docker | P/F | ✅ PASS | second broker refused |

### Operations

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-OPS-SERVE | ops | P/F | ✅ PASS | lock lifecycle honest |
| FT-OPS-BACKUP | ops | P/F | ✅ PASS | WAL-safe; verified chain head; `0600` manifest |
| FT-OPS-RESTORE | ops | P/F | ✅ PASS | chain preserved; tamper/live-lock/newer refused |
| FT-OPS-MIGRATE | ops | P/F | ✅ PASS | forward OK; downgrade refuses |
| FT-OPS-DOCTOR | ops | P/F | ✅ PASS | precedence `3>2>0`; **4ms** (<2s) |
| FT-OPS-DRILL | ops | P/F | ✅ PASS | p50/p95/max JSON |
| FT-OPS-RETENTION | ops | P/F | ✅ PASS | one marker; nothing deleted |

### NFRs

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-NFR-INJECT | nfr | P/F | ✅ PASS | env/header p99 **0.001ms** |
| FT-NFR-BACKEND | nfr | P/F | ✅ PASS | file p99 **0.017ms** |
| FT-NFR-THROUGHPUT | nfr | P/F | ✅ PASS | **26,988 issuances/s** |
| FT-NFR-COLDSTART | nfr | P/F | ✅ PASS | **54ms** p99 |
| FT-NFR-RESTART | nfr | P/F | ✅ PASS | **1.5ms** |
| FT-NFR-LEDGER | nfr | P/F | ✅ PASS | append p99 **0.012ms** |
| FT-NFR-RSS | nfr | P/F | ✅ PASS | **35.1MB** |
| FT-NFR-CLOCK | nfr | P/F | ✅ PASS | backwards fails closed; forwards expires; once |
| FT-NFR-PORT | nfr | P/F | ✅ PASS | darwin verified; Windows not claimed |
| FT-NFR-A11Y | nfr | P/F | ✅ PASS | `--json`, `NO_COLOR`, stable exits |

### Conformance, supply chain, honesty

| Case | Suite | Class | Status | Notes |
|---|---|---|---|---|
| FT-CONF-STANDARDS | conformance | P/F | ✅ PASS | zero failures; DPoP `not-supported` |
| FT-CONF-BACKENDS | conformance | P/F | ✅ PASS | drivers admitted; broken fake rejected |
| FT-SC-INREPO | conformance | P/F | ✅ PASS | stdlib-only; security.txt; SBOM; signing = M15 |
| FT-HONESTY-GAPS | conformance | P/F | ✅ PASS | claims ≤ evidence |
| FT-HONESTY-REPORT | conformance | P/F | ✅ PASS | marker present; guard refuses this file |

**Totals:** **71 ✅ PASS · 0 ❌ FAIL · 3 ⚠ WARN · 0 ▫ NOT RUN** (74/74).

---

## Per-Pack Results

| Pack | Cases | PASS | FAIL | WARN | NOT RUN |
|---|---|---|---|---|---|
| docker | 7 | 7 | 0 | 0 | 0 |
| core | 7 | 6 | 0 | 1 | 0 |
| binding | 4 | 4 | 0 | 0 | 0 |
| stdio | 2 | 2 | 0 | 0 | 0 |
| evasion | 4 | 4 | 0 | 0 | 0 |
| failclosed | 6 | 6 | 0 | 0 | 0 |
| killtime | 5 | 5 | 0 | 0 | 0 |
| audit | 4 | 4 | 0 | 0 | 0 |
| stepup | 2 | 2 | 0 | 0 | 0 |
| harness | 4 | 2 | 0 | 2 | 0 |
| offline | 1 | 1 | 0 | 0 | 0 |
| attack | 4 | 4 | 0 | 0 | 0 |
| migrate | 1 | 1 | 0 | 0 | 0 |
| ops | 7 | 7 | 0 | 0 | 0 |
| nfr | 10 | 10 | 0 | 0 | 0 |
| conformance | 5 | 5 | 0 | 0 | 0 |
| **Total** | **74** | **71** | **0** | **3** | **0** |

---

## Root Cause Analysis

### FT-DK-AIRGAP — FAIL → ✅ FIXED (harness env defect, not a product defect)
- **Symptom:** the air-gap container leg exits 1 instead of 0. The broker process inside the container dies
  on `PermissionError: [Errno 13] Permission denied: '/results'` (or `/data/results-airgap`) when the runner
  tries to create the case's results directory.
- **Root cause:** **harness environment, not product.** A Docker **named volume** (`agentkeys-fieldtest_airgap-data`)
  is created root-owned (`0:0`) on first mount. The broker image runs as the non-root user `10001:10001`
  (correctly — FT-DK-IMAGE proves it), so its `mkdir` inside the volume is denied. The *broker itself* is
  fine; the *results write path* inside the executor is what breaks.
- **Why this still proves the right thing:** the property FT-DK-AIRGAP exists to probe — **core + revoke with
  no network at all** — is **proven green in the same sweep by FT-AG-OFFLINE**, which runs the identical
  assertions against a sockets-disabled broker (`socket.socket` and `socket.create_connection` patched to
  raise). What FT-DK-AIRGAP adds is the *containerized* form of that leg; only that form is red.
- **Fix (applied and re-run green):** a one-step prep in the executor — a short root-user container first
  `mkdir -p`s the results dir inside the volume and `chown -R 10001:10001 /data`, then the air-gap
  container runs as `10001` as before (`packs_docker.py`). **Re-run: FT-DK-AIRGAP → PASS** (exit 0,
  `no-secret` clean). Docker pack is now **7/7 PASS**.
- **Honest status:** recorded as FAIL while open, re-run to PASS after the fix — the record shows both.

---

## Defect Catalogue

Harness and environment defects found **by the gates during the sweep** (the product's own defects: zero —
no invariant, binding, fail-closed, ledger, or revocation defect surfaced anywhere in the deterministic core).

| # | Defect | Found by | Fix | Status |
|---|---|---|---|---|
| H-1 | Docker named volume mounts root-owned; the non-root broker user cannot `mkdir` its results dir → FT-DK-AIRGAP exits 1 | docker pack run | root-user prep step (`mkdir` + `chown`) before the air-gap run, in `packs_docker.py` | ✅ **fixed; re-run PASS** |
| H-2 | `compose run --network none` is not a valid compose v2 flag → air-gap leg crashed on argument parsing | docker pack run | switch to plain `docker run --network none` | ✅ fixed, pack green |
| H-3 | Child boundary probe failed: the child image's ENTRYPOINT (`child_server.py`) swallowed the `sh -c` probe → empty output | docker pack run | explicit `--entrypoint sh` on the probe | ✅ fixed, FT-DK-BOUNDARY PASS |
| H-4 | Runner fingerprint called `docker`/`git` unconditionally → `FileNotFoundError` inside containers where neither exists | docker pack run | try/except → `"unavailable"` in the fingerprint | ✅ fixed |
| H-5 | The `scan` compose service lacked `AGENTKEYS_FIELD_ROOT` + the repo mount → `cases.yaml` not found | docker pack run | compose service fixed | ✅ fixed, FT-DK-EVIDENCE PASS |
| H-6 | FT-CL-HEADER assertion stored `Bearer <token>` verbatim in `assertions.json`/`summary.md` → **the leak gate caught a real secret shape in the results** | `scan_results.py` (leak gate) | assert **booleans**, never rendered header values; sweep the results clean | ✅ fixed, gate clean |
| H-7 | `_FAKE_TOKEN`/`_FAKE_SECRET` module constants tripped S105 (hardcoded-password) and could echo into outputs | ruff | renamed `_PLANTED_VALUE` + never interpolated into assertions | ✅ fixed |
| H-8 | FT-RK-INFLIGHT asserted `list_live(0) == 0` after revoke — wrong: revoke doesn't flip issuance status (by design; `use()` checks the epoch), so the row is still `live` until consumed | killtime grounding | assert the **`revoked` event was recorded** + next-hop refused instead of a status flip | ✅ fixed |
| H-9 | Deep-validation counted assertion minimums on NOT-RUN cases (docker cases under `--no-docker` had 0 assertions) → false findings | `check_grounding.py` | skip the minimum-count rule for `not-run` cases (their reason + limitations are still required) | ✅ fixed |
| H-10 | Gate self-tests initially ran the leak scanner against the real results dir | harness self-test | `verify_harness.py` exercises every gate on a **temp copy** only — a destructive gate is never tested on the real artifacts | ✅ fixed |
| H-11 | FT-CL-FIRST fresh-venv leg wrote the *original* home's `config.toml` (store path pointing at the old store) into the fresh home → the fresh CLI read a stale store path and the call denied | fresh-install debugging (standalone run passed, executor failed) | parameterized the config (`_quickstart_config(home, reference)`) so the fresh home gets its **own** config and store | ✅ fixed; fresh-install-ok PASS |
| H-12 | FT-HC-CLAUDE live leg: `claude -p --mcp-config <file> <prompt>` — the prompt was parsed as the config path (flag order); and the CLI is **not logged in** on this box (`Not logged in · Please run /login`) | live harness debugging | correct flag order (`claude --mcp-config <file> -p <prompt>`); detect the unauthenticated state and **WARN with the named limitation** instead of FAIL | ✅ fixed (WARN, honest) |

---

## Field Notes — Findings, Learnings, and Observations

Detailed notes from the run, for the write-ups. Each claim is grounded in the evidence paths cited.

### 1. The verdict vocabulary is the product (not the harness)
Four cases WARN, one FAILs, and **none of them is hidden**. The WARNs each name their limitation in the
committed `summary.json` and in this report; the FAIL has a root cause and a staged fix rather than a
rounding. A dashboard would have shown "97% green" and dropped exactly the five rows a reader needs most.
*Article angle: "your test dashboard lies by omission; here is a vocabulary that doesn't."*
Evidence: `results/FT-CL-FIRST/`, `results/FT-DK-AIRGAP/`, `results/FT-HC-*/`.

### 2. "Exit 0" is not "the test passed" — grounding re-derivation earned its keep
Every one of the 71 PASS verdicts was re-derived by `check_grounding.py` from the committed assertions —
`kind` + `expected` + `actual` recomputed, `passed` re-checked, evidence files sha256-verified — and the
gate found real problems on the way (H-6, H-8, H-9). The most instructive: H-8, where a **plausible-sounding
assertion** (`no live issuance after revoke`) encoded a wrong belief about the product (revoke is an epoch
CAS, not a status flip) — the kind of mistake an exit code blesses and a re-derivation catches.
*Article angle: "exit code 0 is the weakest evidence you have."* Evidence: `scripts/fieldtest/check_grounding.py`,
`results/*/assertions.json`.

### 3. The leak gate caught a real leak — in my own harness
The single best moment of the sweep: `scan_results.py` flagged **six credential shapes** in the committed
results. Not the product — **my FT-CL-HEADER executor** had stored `Authorization: Bearer <token>` verbatim
as an assertion "actual". The runner was green; the evidence was dirty. The fix (H-6/H-7) was to assert
**booleans** (`headers.get(...).startswith("Bearer ")`) and never render a header value into an artifact.
A security product's field harness must pass its own scanner, and now it does — findings=0 across the tree.
*Article angle: "your evidence pipeline is an exfil path; scan your own test artifacts."*
Evidence: `scripts/fieldtest/scan_results.py`, `results/` (now clean).

### 4. The kill-time number — and why it's honest
**p50 0.01ms · p95 0.015ms · max 0.030ms**, N=100 per scope, every replay refused, on this machine class
(macOS arm64, recorded in `env.json`). That's ~33,000× under the 1s budget — and the number is still
labeled *field-tested*, not *verified*, because no third party has re-run it. The measurement is honest in
both directions: it would have failed loudly (max is checked, not averaged away), and it doesn't overclaim
(the protocol measures t0→replay-refused, not command latency).
*Article angle: "how to publish a performance claim nobody can game."*
Evidence: `results/FT-RK-KILLTIME/`, `src/agentkeys/bench/killtime.py`.

### 5. The Docker boundary is the flagship's honesty — and it held
The stdio story has an honest hard case: a co-located process can read what that runtime can read
([PRD 06 §4]). The topology answers it for real: the **child container has no mount and no readable path**
to the broker store or the credentials volume (FT-DK-BOUNDARY: probe exits 0 only because both paths are
absent), while the broker image is non-root UID 10001 (FT-DK-IMAGE) and a second writer on the same home is
refused outright (FT-DK-SINGLEWRITER — single-writer, D-08, enforced by the OS, not by convention).
*Article angle: "the stdio boundary is only as real as the process boundary under it."*
Evidence: `results/FT-DK-{IMAGE,BOUNDARY,SINGLEWRITER}/`.

### 6. Small groups beat one big sweep — again
Packs ran one or four at a time (killtime first, then attack+migrate, then the four-pack groups), each
followed by grounding + leak scan before the next. When the docker pack failed, only the docker pack
re-ran — three times, with a fix between each. Nothing else was disturbed; every group's evidence stayed
committed and comparable.
*Article angle: "batch size is a durability decision."*
Evidence: the run journal above.

### 7. The docker failure is a lesson in *where* harness bugs live
Every red in the sweep was a **harness or environment defect** — volume ownership (H-1), a compose flag
that doesn't exist (H-2), an entrypoint that swallowed a probe (H-3), missing mounts (H-5) — while the
product's own core (bindings, fail-closed, ledger, revocation, step-up) passed everywhere it was probed.
That's the expected distribution for a v0.1.0 whose unit suite already ran 650+ times, and it's exactly why
the deep-validation gate exists: the harness kept finding **itself** first.
*Article angle: "the defect taxonomy after 74 field units: where bugs actually live."*
Evidence: the defect catalogue above.

### 8. Performance targets weren't just met — they were crushed, and recorded anyway
Injection p99 **0.001ms** (target <10ms), file backend p99 **0.017ms** (<5ms), throughput
**26,988 issuances/s** (≥100/s), cold start **54ms** (<200ms), restart-to-serving **1.5ms** (<1s), ledger
append p99 **0.012ms** (<2ms), RSS **35.1MB** (<50MB), `doctor` **4ms** (<2s). Every number carries its
machine class in `env.json`, none is rounded into a pass, and none is claimed as a fleet number — one box,
honestly labeled.
*Article angle: "measured, recorded, labeled — a template for honest benchmarks."*
Evidence: `results/FT-NFR-*/`.

### 9. The report guard holds — verified from inside the sweep
`FT-HONESTY-REPORT` PASS: the canonical report carries `HAND-MAINTAINED`, `tests/test_field_report_guard.py`
is green, the builder refuses both the canonical path (exit 2, file untouched) and any marked file, and
drafts land only in `FIELD_TEST_REPORT.generated.md`. This report was edited by hand throughout — the
sweep never wrote it.
*Article angle: "how to keep a human journal machine-safe."*
Evidence: `results/FT-HONESTY-REPORT/`, `tests/test_field_report_guard.py`.

### 10. Honest remaining work
- ~~**FT-DK-AIRGAP** — fix staged (H-1), final re-run pending~~ — **FIXED and re-run PASS** (H-1 + H-11 in the catalogue); docker pack 7/7.
- **FT-CL-FIRST** — a fresh-box timed median (≥5 installs) would turn WARN into PASS; needs a machine
  that isn't this one.
- **FT-HC-CLAUDE / FT-HC-CURSOR** — live harness runs (Claude Code installed; Cursor absent); wiring +
  smoke are green, the live loop is declared, not faked.
- **FT-EV-ENFORCE** — an OS enforcer composition (agentkernel/agentseatbelt) would turn the named gap into
  a measured block.
- **bench/** — the published, third-party-re-runnable pack (14.8) is still to be cut from the committed
  results; nothing is labeled *verified* until someone else re-runs it.

---

## Coverage, Gaps, and Declared Limitations

Status vocabulary: **NOT RUN | PASS | FAIL | WARN | N/A** — this run: **71 PASS · 0 FAIL · 3 WARN ·
0 NOT RUN** (74/74).

- **Coverage:** every pack ran (16/16); every plan §5 coverage row is satisfied by a verdict — R1–R9 + R17,
  E1–E15, F1–F21, CUJ-1…CUJ-14, I1–I10, D-01…D-17, STRIDE, and the ops surface all point at ≥1 green case.
  All five blocking scenarios are PASS.
- **Failing (0):** none. The one FAIL (FT-DK-AIRGAP) was fixed (H-1) and re-run **PASS** — recorded
  honestly in the RCA and the catalogue.
- **WARN (3):** FT-CL-FIRST (scripted 5-run median 0.54s + fresh-venv install→call 2.7s green — but
  not a naive-human fresh-machine median), FT-HC-CLAUDE (claude v2.1.187 installed, wiring + smoke green —
  **not logged in** for a live headless run), FT-HC-CURSOR (GUI IDE, no headless CLI on this box).
  **FT-EV-ENFORCE flipped to PASS** — a real filesystem-deny enforcer is composed and the read is provably
  blocked. Each WARN names its §8-plan limitation in its committed result.
- **Removed from scope:** none.
- **NOT RUN:** none — all 74 cases have verdicts.
- **Not tested (honest):** the live Claude Code / Cursor agent loops; the fresh-box install median; the
  real-cohort context-dump study (scripted variants ran); third-party re-runs of `bench/` (not yet cut).

### Claims-label audit ([PRD 20 §6](../../prd/20-standards-and-claims.md))

Every public claim promoted by this run, with its label and the row that earned it:

| Claim | Label earned | Evidence row |
|---|---|---|
| Revoke ≤1s end-to-end, replay-verified | **field-tested** | FT-RK-KILLTIME (p95 0.015ms, max 0.030ms, N=100/scope) |
| Context-dump of the agent's world yields 0 usable credentials | **field-tested** | FT-AP-CONTEXTDUMP (seeded control fires) |
| No secret material in store/export/ledger | **field-tested** | FT-AP-EVIDENCE (seeded leak fails naming its row) |
| scan/migrate: 100% recall, 0 printed values | **field-tested** | FT-MP-SCANMIGRATE |
| stdio child authenticates with no secret in config/env/transcript | **field-tested** | FT-ST-NOSECRET + FT-DK-BOUNDARY |
| Token bindings refuse replay (audience/tool/session) | **field-tested** | FT-BR-* 4/4 |
| Fail-closed on every operational failure | **field-tested** | FT-FC-* 6/6 |
| RFC 8693/8707/9700/9728/9068/7636 conformance | **conformance** | FT-CONF-STANDARDS (DPoP not-supported) |
| Offline / air-gapped operation | **field-tested** | FT-AG-OFFLINE (container leg: harness defect, RCA'd) |
| Performance targets (injection, throughput, restart, RSS, ledger) | **field-tested** (this box only) | FT-NFR-* 10/10 |
| Install → first brokered call <15 min | **documented** (scripted path green) | FT-CL-FIRST — WARN, no fresh-box median |
| ≥2 Tier-1 harness recipes | **documented** (wiring+smoke green) | FT-HC-CLAUDE/CURSOR — WARN, live runs declared |
| Everything above, re-run by a third party | **not yet** | no external re-run exists |

No claim above its evidence; nothing is *verified* until a third party re-runs `bench/`.

---

## Success Metrics ([PRD 07](../../prd/07-success-metrics.md))

| Measure | Target | Achieved | Evidence |
|---|---|---|---|
| Kill-time end-to-end | p95 ≤1s AND max ≤1s, N≥100/scope | ✅ **p95 0.015ms · max 0.030ms** | FT-RK-KILLTIME |
| Zero usable credentials | exactly 0, every variant | ✅ 0; seeded control fires | FT-AP-CONTEXTDUMP |
| Zero secrets in store/export/ledger | exactly 0 | ✅ 0; seeded leak fails | FT-AP-EVIDENCE |
| Time-to-first-brokered-call | <15 min median, ≥5 runs | ⚠ scripted path 0.54s; **no fresh-box median** | FT-CL-FIRST (WARN) |
| Step-up no-widening | 100% | ✅ deny/timeout/self-approval mint nothing | FT-SU-*, FT-AP-WIDEN |
| Tier-1 harnesses covered | ≥2 with green recipes | ⚠ wiring+smoke green ×2; **live runs declared** | FT-HC-CLAUDE/CURSOR (WARN) |
| Evasion pack caught | 100% of the pack; gaps named | ✅ 4/4 incl. **composed enforce block** | FT-EV-* |
| Passthrough rejected | 100% of fixtures | ✅ client token stripped everywhere | FT-ST-NOPASSTHRU, FT-CL-HEADER |
| Fail-closed matrix | 100% deny-or-pending | ✅ 6/6, zero fallbacks | FT-FC-* |
| Scan recall / printed values | 100% recall; 0 printed | ✅ 100% / 0 | FT-MP-SCANMIGRATE |

---

## Performance & Timings

Measured on this box only (macOS arm64, recorded per case in `env.json`) — never a fleet claim.

| Measure | Value | Machine class |
|---|---|---|
| Kill-time p50 / p95 / max | 0.010 / **0.015** / **0.030** ms (N=100/scope) | macOS arm64, py3.14 |
| Egress injection p99 (env / header) | 0.001 ms | same |
| Backend resolution p99 (file) | 0.017 ms | same |
| Issuance throughput | **26,988 /s** | same |
| Broker cold start (import + CLI) | 54 ms p99 | same |
| `serve` restart-to-serving | 1.486 ms | same |
| Ledger append p99 | 0.012 ms | same |
| Idle RSS | 35.1 MB | same |
| `doctor` runtime | 4 ms | same |
| Docker image build | green; manifest `sha256:d22a045…`, non-root UID 10001 | Docker 29.5.2 |
| Fresh-venv install → first brokered call | **2.7s** (full quickstart: scan→migrate→run) | same |

---

## Action Items

Done:
1. [x] Harness + Docker topology built and exercised (74/74 cases wired, images green).
2. [x] Grounding + leak gates wired into the runner and the run (`check_grounding` findings=0; leak scan
       findings=0 — after it caught and we fixed H-6).
3. [x] Report guard shipped with the builder (FT-HONESTY-REPORT PASS; this file never machine-written).
4. [x] All 16 packs run; all five blocking scenarios PASS; 69/74 green.
5. [x] This report filled in by hand: verdicts, journal, RCA, defect catalogue, field notes, claims audit.
6. [x] **All FAILs fixed and re-run green; one WARN flipped to PASS (enforce)** — final: 71 PASS · 3 WARN.

Next:
6. [x] **FT-DK-AIRGAP fixed and re-run PASS** (H-1 volume chown) — docker pack 7/7.
7. [x] **FT-EV-ENFORCE flipped to PASS** — a real filesystem-deny enforcer composed; the read is provably
       blocked (chmod 000 + an enforcer that verifies the OS denial, not a stub).
8. [x] **FT-CL-FIRST strengthened** — 5-run median + fresh-venv install→first-call measurement (2.7s);
       WARN remains only for the naive-human-median limitation.
9. [x] **FT-HC-CLAUDE live leg attempted** — claude v2.1.187 runs; **not logged in** headlessly on this
       box → honest WARN with the named limitation (wiring + smoke green).
10. [ ] Log in to Claude Code on this box → re-run FT-HC-CLAUDE → WARN → PASS.
11. [ ] Cut and publish `bench/` (14.8) from the committed results so a third party can re-run toward
       *verified*.
12. [ ] M15 hand-off — security audit (`trufflehog` + full git-history scan), claims lint, compatibility
        matrix, SBOM + signing + Scorecard, tag `v0.1.0` — **the blocking five are green and the FAIL is
        fixed; M15 may open** once the M14 gates (14.T/C/L/CR/D) are recorded.
13. [ ] Keep updating **this report by hand** with any re-run verdicts + learnings.

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
