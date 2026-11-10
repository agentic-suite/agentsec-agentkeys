# Field-Test Plan — agentkeys v0.1.0

**Milestone:** M14 (#172–#185) · **Authored:** `14.D0` (#172), 2026-11-09 · **Plan →**
`docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` (hand-maintained) · **Runner:** `scripts/fieldtest/run_pack.py`
+ `python -m agentkeys.fieldtest` · **Cases:** `field-test/v0.1.0/cases.yaml` · **Results:**
[`field-test/v0.1.0/results/`](../../../field-test/v0.1.0/results/) · **Docker:**
`field-test/v0.1.0/docker/` · **Bench:** `bench/`.

**BLUF.** Prove v0.1.0 on the real CLI, store, ledger, stdio wrapper, and Docker topology: agents hold
references, the broker injects scoped tokens at egress, `revoke` kills in ≤1s (replay-verified), a context
dump finds zero usable credentials, scan/migrate moves secrets out of `.env` with zero values printed, and
tamper fails closed. The matrix below is frozen; M14 is **running, not deciding**. Verdicts are entered
**by hand** from committed results — no automation writes the report ([PRD 21 §5](../../prd/21-evidence-register-and-method.md),
[AGENTS.md](../../../AGENTS.md)).

Sources: [WBS Part 8](../../wbs/v0.1.0/wbs-v0.1.0-part8-fieldtest-release.md) ·
[PRD 04](../../prd/04-users-and-cujs.md) · [PRD 05](../../prd/05-features.md) ·
[PRD 06](../../prd/06-security-baseline.md) · [PRD 07](../../prd/07-success-metrics.md) ·
[PRD 08](../../prd/08-risks.md) · [PRD 09](../../prd/09-roadmap.md) · [PRD 11](../../prd/11-decisions.md) ·
[PRD 12](../../prd/12-traceability.md) · [PRD 13](../../prd/13-non-functional-requirements.md) ·
[PRD 16](../../prd/16-adapters-and-integration.md) · [PRD 17](../../prd/17-scenarios.md) ·
[PRD 19](../../prd/19-harness-compatibility.md) · [PRD 20](../../prd/20-standards-and-claims.md) ·
[PRD 21](../../prd/21-evidence-register-and-method.md) ·
[PRD 22](../../prd/22-operations-and-governance.md) ·
[PRD 23](../../prd/23-enterprise-adoption-and-hardening.md) ·
[revoke design](../../design/v0.1.0/revoke.md) · [ledger design](../../design/v0.1.0/ledger.md) ·
[egress design](../../design/v0.1.0/egress.md) · [stdio design](../../design/v0.1.0/stdio.md) ·
[ops design](../../design/v0.1.0/ops.md) ·
[honest gaps](../../explanation/honest-gaps.md).

---

## 1. Scope

**In scope:** SC-01–SC-43 + SC-51; features F1–F21; R1–R9 + R17; E1–E15; CUJ-1…CUJ-14; invariants I1–I10;
risks R-1…R-12; decisions D-01…D-17; the STRIDE rows of [PRD 06 §2](../../prd/06-security-baseline.md);
the ops surface ([PRD 22](../../prd/22-operations-and-governance.md)); the standards suites
([PRD 20 §1](../../prd/20-standards-and-claims.md)).

**Out of scope, never scored:** SC-44–SC-50, SC-53 (forward slate); F22 `posture` (v0.1.x); F23 canaries
(P2); DPoP/RFC 9449 (v0.3.0); cloud backends (R10); fleet/server mode (R11); signed release + SLSA +
Scorecard attestations (**M15**); `init`/`context-dump`/`scan-usable` (stubs — the quickstart writes the
config directly).

## 2. Rules

1. **No silent skips.** Every case is **PASS / FAIL / WARN / NOT RUN** ([PRD 17 §16](../../prd/17-scenarios.md)).
   A `P/F` case that cannot run is a **FAIL of the run**. `WARN` only for the four `P/F|W` cases, with a
   named limitation in the report. `NOT RUN` on a blocking case blocks M15.
2. **Blocking:** SC-24 (kill-time), SC-40 (context-dump), SC-41 (tamper), SC-43 (evidence), SC-51
   (scan/migrate). `P/F` only — no WARN, no NOT RUN.
3. **Verify the verifier.** Blocking packs ship a falsification control (seeded secret/leak/broad-reuse). A
   silent scanner fails the run.
4. **Determinism.** No ML, no decision-affecting randomness, no network in the decision path. The same pack
   reproduces its JSON except timings.
5. **No real secrets.** Fake fixtures only; the single live value is an operator throwaway token, never
   printed or committed.
6. **One harness.** The runner drives the shipped primitives only — the `agentkeys` CLI,
   `agentkeys.bench.killtime`, `agentkeys.evidence`, `agentkeys.attackpacks`, `agentkeys.invariants`,
   `agentkeys.conformance`, `agentkeys.ops`, `agentkeys.recipes`, `agentkeys.scan`/`migrate`, and the
   stdio wrapper. No parallel implementation.
7. **The report is hand-written.** `FIELD_TEST_REPORT.md` carries the `HAND-MAINTAINED` marker;
   `tests/test_field_report_guard.py` proves a writer refuses to write/rewrite/regenerate/move/truncate/delete
   it. Automated drafts may write only `FIELD_TEST_REPORT.generated.md` and never a marked file.

## 3. Docker topology (reference environment)

v0.1.0's broker is a **CLI, not a daemon** — every command runs the broker logic in-process against the
store; `agentkeys serve` only holds the store and a lock file
([ops design](../../design/v0.1.0/ops.md)). The topology reflects that:

```
docker network "fieldtest" (internal)
  broker    non-root UID; store volume + credentials volume (both 0600, broker-only).
            Runs the CLI, `agentkeys run -- <child>` (stdio children are broker-container
            subprocesses — that is what the code does), and the packs.
  child     fixture stdio MCP server / CLI child as a SEPARATE container with NO store or
            credentials mount. It receives only the scoped token (documented handoff via
            `docker run -e`), authenticates to the fake upstream, and proves the token
            crossed a container boundary while the backend secret never left the broker.
  upstream  fake HTTP resource recording every received header + fake RFC 8693 STS.
  airgap    network_mode: none client (core + revoke with no egress at all).
  scan      evidence scanner over the broker volumes (mounted read-only).
```

- **Isolation fact:** the child container has no path to the store or the backend credential file — that is
  the process boundary [PRD 06 §4](../../prd/06-security-baseline.md) makes load-bearing; a co-located
  subprocess is a named limitation (§8), never claimed.
- Non-root everywhere; `TZ=UTC`, `LC_ALL=C`, `NO_COLOR=1`; Python 3.12 slim pinned **by digest**.
- Each result records image digests, OS/arch/CPU class, python, git SHA, and the compose hash
  ([PRD 21 §6](../../prd/21-evidence-register-and-method.md) hardware disclosure).
- **Docker is required for M14.** The `FT-DK-*` cases are `P/F`: no Docker, no green field test. The local
  venv runs L0 only.

## 4. Case matrix

`Env`: `ci` = no network/harness; `file` = file backend; `docker` = topology; `harness` = Tier-1 harness;
`human` = field box / operator cohort. `Class`: `P/F`, or `P/F|W` (WARN with a §8 limitation).

### Core lifecycle (SC-01–07)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-CL-FIRST | SC-01 | install → first brokered call <15 min, no code change; median of ≥5 fresh runs | human,docker | P/F\|W |
| FT-CL-ENV | SC-02 | env injection via `AGENTKEYS_SCOPED_TOKEN=akref:…` placeholder; 0 secret bytes in transcript/args | ci,file,docker | P/F |
| FT-CL-HEADER | SC-03 | header injection; upstream capture shows the broker token, client token absent | ci,docker | P/F |
| FT-CL-EXCHANGE | SC-04 | RFC 8693; audience==target, scope==tool, `act` present, client token absent | ci,docker | P/F |
| FT-CL-TTL | SC-05 | expiry fires exactly once; no post-TTL use | ci | P/F |
| FT-CL-ROTATE | SC-06 | backend value rotated; next resolve uses it, no restart; pre-rotation token dead within TTL | ci,file | P/F |
| FT-CL-TWOHARNESS | SC-07 | two sessions, one reference; both authenticate; one revoke kills both | ci | P/F |

### Binding / replay (SC-08–11)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-BR-AUDIENCE | SC-08 | wrong audience refused + `exchange-rejected` event; no second success | ci | P/F |
| FT-BR-TOOL | SC-09 | wrong tool/scope refused + event | ci | P/F |
| FT-BR-SESSION | SC-10 | replay after session end refused | ci | P/F |
| FT-BR-STALE | SC-11 | stale / forwarded / widened all refuse; injector cannot widen | ci | P/F |

### stdio (SC-12–13)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-ST-NOSECRET | SC-12 | child authenticates; scan of child config + env + transcript + parent env finds 0 usable secrets | ci,docker | P/F |
| FT-ST-NOPASSTHRU | SC-13 | client token in the child request is stripped; upstream gets the broker token only | ci,docker | P/F |

### Evasion (SC-14–17)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-EV-DOTENV | SC-14 | `.env` read → high `evasion-detected`, attributed | ci,docker | P/F |
| FT-EV-CLOUD | SC-15 | cloud credential file read caught, path named | ci | P/F |
| FT-EV-KEYCHAIN | SC-16 | keychain read caught, attributed | ci | P/F |
| FT-EV-ENFORCE | SC-17 | blocked only where an enforcer composes; otherwise a named gap, never a claimed block | ci | P/F\|W |

### Fail-closed (SC-18–23)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-FC-LOCKED | SC-18 | locked backend → deny on every path; no static/env fallback; `doctor` explains | ci | P/F |
| FT-FC-ABSENT | SC-19 | absent backend → deny; no fallback | ci | P/F |
| FT-FC-CONFIG | SC-20 | ambiguous config → loud refusal naming the field | ci | P/F |
| FT-FC-STORE | SC-21 | corrupt store → no new issuance; `doctor` non-zero | ci | P/F |
| FT-FC-SINK | SC-22 | sink offline → one `sink-gap` marker; local chain intact; nothing lost | ci | P/F |
| FT-FC-CRASH | SC-23 | `kill -9` mid-issue → restart recovers; retry returns the **same** issuance (exactly-once, E1/E2) | ci,docker | P/F |

### Revocation / kill-time (SC-24–28)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-RK-KILLTIME | **SC-24** | N≥100 per scope (`session`/`agent`/`all`); **p95 ≤1s AND max ≤1s**; replay provably refused | ci,docker,mac,lin | **P/F** |
| FT-RK-SCOPE | SC-25 | scoped revoke kills only the target; `--all` explicit | ci | P/F |
| FT-RK-INFLIGHT | SC-26 | in-flight call's next hop fails; no completion after revoke | ci | P/F |
| FT-RK-UNKNOWN | SC-27 | unknown target → non-zero naming the target | ci | P/F |
| FT-RK-ATTR | SC-28 | `revoked` carries principal + target + timestamp | ci | P/F |

### Lifecycle audit (SC-29–32)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-LA-EXPORT | SC-29 | ordered timeline + chain; joins by `session_id`; **two exports byte-identical** | ci,docker | P/F |
| FT-LA-TAMPER | SC-30 | rewritten/deleted row detected, first bad seq named, never skipped | ci | P/F |
| FT-LA-NOSECRET | SC-31 | 0 usable secrets in the export | ci | P/F |
| FT-LA-EVENT | SC-32 | one event per transition with `event_version`; lifecycle fields carry the OTel GenAI shape (`gen_ai.tool.name`/`gen_ai.agent.id` mappings, [PRD 20 §1](../../prd/20-standards-and-claims.md)) | ci | P/F |

### Step-up (SC-33–34)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-SU-APPROVED | SC-33 | no mint before approval; tighter TTL; `provenance` + `step-up-granted` after the mint; same-window retry not re-asked | ci | P/F |
| FT-SU-DENIED | SC-34 | deny / timeout / self-approval mint nothing; structured deny | ci | P/F |

### Harness compatibility (SC-35–38)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-HC-CLAUDE | SC-35 | Claude Code recipe → authenticated call; transcript only the reference; no fork; **tested version recorded** | harness | P/F\|W |
| FT-HC-CURSOR | SC-36 | Cursor recipe → authenticated call; same wrapper; version recorded | harness | P/F\|W |
| FT-HC-GENERIC | SC-37 | generic MCP client / SDK: issue → use → revoke via the public contract | ci | P/F |
| FT-HC-NOTYET | SC-38 | uncovered harness labelled not-yet; gap named | ci | P/F |

### Air-gap (SC-39)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-AG-OFFLINE | SC-39 | resolve/use/revoke with the network off; unknown cloud backend warns + refuses; `doctor` explains | ci,docker | P/F |

### Attack packs (SC-40–43 + STRIDE)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-AP-CONTEXTDUMP | **SC-40** | 0 usable credentials in every variant; seeded control fires | ci,docker,human | **P/F** |
| FT-AP-TAMPER | **SC-41** | config edit / kill broker / spoof reference / ledger rewrite all deny + emit an event | ci,docker | **P/F** |
| FT-AP-WIDEN | SC-42 | widening refused at the binding; logged | ci | P/F |
| FT-AP-EVIDENCE | **SC-43** | 0 secrets in store/export/ledger; seeded leak fails naming the row; receipts present | ci,docker | **P/F** |
| FT-AP-FLOOD | — (STRIDE DoS, [PRD 06 §2](../../prd/06-security-baseline.md)) | flood resolution; every call evaluated; fail closed under load, never fail open; no unsafe default | ci,docker | P/F |

### Migration (SC-51)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-MP-SCANMIGRATE | **SC-51** | 100% recall on the seeded corpus; **0 printed values**; every use site rewritten; failed migrate leaves files byte-identical; re-scan closes the finding; broad reuse flagged | ci | **P/F** |

### Docker topology

| ID | Check | Env | Class |
|---|---|---|---|
| FT-DK-IMAGE | broker image non-root, pinned by digest, secret-free; in-container `doctor` green | docker | P/F |
| FT-DK-COMPOSE | topology healthy; store + credentials `0600`, broker-only | docker | P/F |
| FT-DK-QUICKSTART | the documented quickstart inside the broker container ends in a brokered call | docker | P/F |
| FT-DK-BOUNDARY | the **child container** has no mount or readable path to the store or the backend credentials; the only credential-shaped value it holds is the scoped token; a read attempt is recorded | docker | P/F |
| FT-DK-AIRGAP | `--network none` run passes core + revoke; no egress attempted | docker | P/F |
| FT-DK-EVIDENCE | evidence service scans the broker volumes: 0 secrets; seeded leak fails | docker | P/F |
| FT-DK-SINGLEWRITER | two broker containers, one shared store: the second refuses (single writer, D-08) | docker | P/F |

### Operations (M12 / [PRD 22](../../prd/22-operations-and-governance.md))

| ID | Check | Env | Class |
|---|---|---|---|
| FT-OPS-SERVE | live lock refuses a second serve; stale lock reported by `doctor`; SIGTERM closes + removes the lock | ci,docker | P/F |
| FT-OPS-BACKUP | WAL-safe backup; manifest with chain head; `0600` | ci | P/F |
| FT-OPS-RESTORE | tampered backup / live broker / newer schema all refused; restored chain verifies **before** serving | ci | P/F |
| FT-OPS-MIGRATE | an older store migrates forward; a newer schema refuses loudly and writes nothing | ci | P/F |
| FT-OPS-DOCTOR | chain / serve-lock / config-integrity checks, exit precedence `3 > 2 > 0`, run <2s | ci | P/F |
| FT-OPS-DRILL | drill emits p50/p95/max + pass/fail JSON; verdict entered by hand | ci,docker | P/F |
| FT-OPS-RETENTION | prune appends one `retention-pruned` marker; deletes nothing; chain intact | ci | P/F |

### NFRs ([PRD 13](../../prd/13-non-functional-requirements.md))

| ID | Check | Target | Env | Class |
|---|---|---|---|---|
| FT-NFR-INJECT | injection latency, measured | env/header <10 ms p99; exchange <50 ms p99 | ci | P/F |
| FT-NFR-BACKEND | backend resolution, measured | file <1 ms p99; keychain <5 ms p99 | ci | P/F |
| FT-NFR-THROUGHPUT | sustained issuances | ≥100 issuances/s | ci | P/F |
| FT-NFR-COLDSTART | broker cold start | <200 ms p99 | ci | P/F |
| FT-NFR-RESTART | `serve` restart-to-serving | <1 s | ci,docker | P/F |
| FT-NFR-LEDGER | ledger append | <2 ms p99 | ci | P/F |
| FT-NFR-RSS | idle RSS | <50 MB | docker | P/F |
| FT-NFR-CLOCK | clock jump cannot extend/resurrect; expiry fires once | E6 | ci | P/F |
| FT-NFR-PORT | macOS + Linux pass; Windows labelled not-yet | §5 | mac,lin | P/F |
| FT-NFR-A11Y | `NO_COLOR` respected; `--json` stable; exit codes stable; UTC times; linear text | §10 | ci | P/F |

A missed performance target is **reported as measured with a finding** — never rounded into a pass, never
labeled above `conformance`. Machine class is recorded with every number.

### Conformance, supply chain, honesty

| ID | Check | Env | Class |
|---|---|---|---|
| FT-CONF-STANDARDS | RFC 8693/8707/9700/9728/9068/7636 green; DPoP reported `not-supported`, never implied | ci | P/F |
| FT-CONF-BACKENDS | file + keychain admitted by conformance; a deliberately broken backend rejected at load | ci | P/F |
| FT-SC-INREPO | stdlib-only runtime deps; `security.txt`; CI gates; SBOM; fuzz targets; image + build-context scan clean | ci,docker | P/F |
| FT-HONESTY-GAPS | every public claim ≤ its evidence label; every gap named ([PRD 20 §6](../../prd/20-standards-and-claims.md)) | ci | P/F |
| FT-HONESTY-REPORT | `HAND-MAINTAINED` marker present; the guard refuses write/rewrite/regenerate/move/truncate/delete | ci | P/F |

**Totals:** 45 scenario/attack cases + 7 Docker + 7 ops + 10 NFR + 5 conformance/honesty = **74 cases**.
`P/F|W` = 4 (FT-CL-FIRST, FT-EV-ENFORCE, FT-HC-CLAUDE, FT-HC-CURSOR) · blocking = 5.

## 5. Coverage

### Features (PRD 05 §C)

| Feature | Cases | Feature | Cases |
|---|---|---|---|
| F1 reference + migration helper | FT-MP-SCANMIGRATE, FT-CL-FIRST | F12 stdio virtualization | FT-ST-*, FT-DK-BOUNDARY |
| F2 env injector | FT-CL-ENV, FT-ST-NOSECRET | F13 step-up | FT-SU-* |
| F3 header injector | FT-CL-HEADER, FT-HC-CURSOR | F14 redactor + receipts | FT-LA-NOSECRET, FT-AP-EVIDENCE |
| F4 exchange injector | FT-CL-EXCHANGE | F15 store + capabilities | FT-FC-CRASH, FT-OPS-*, FT-DK-SINGLEWRITER |
| F5 TTL/audience/tool/session mint | FT-CL-ENV, FT-BR-*, FT-CL-TTL | F16 config model | FT-FC-CONFIG, FT-CL-FIRST, FT-OPS-DOCTOR |
| F6 revoke + kill-time | FT-RK-* | F17 harness recipes | FT-HC-* |
| F7 keychain + file backends | FT-FC-LOCKED/ABSENT, FT-CONF-BACKENDS, FT-CL-ROTATE | F18 conformance kit | FT-CONF-* |
| F8 fail-closed + doctor | FT-FC-*, FT-OPS-DOCTOR, FT-DK-IMAGE | F19 attack packs | FT-AP-*, FT-RK-* |
| F9 ledger + events | FT-LA-EVENT, FT-LA-TAMPER | F20 SDK/CLI contract | FT-HC-GENERIC, FT-LA-EXPORT |
| F10 export + verify-log | FT-LA-EXPORT, FT-LA-NOSECRET, FT-LA-TAMPER | F21 scan/migrate | FT-MP-SCANMIGRATE |
| F11 evasion detect/enforce | FT-EV-* | F22 posture (v0.1.x) · F23 canaries (P2) | not scored — limitation |

### Requirements (PRD 05 §A/§B)

| Req | Cases | Req | Cases |
|---|---|---|---|
| R1 reference-only | FT-CL-ENV, FT-ST-NOSECRET, FT-AP-CONTEXTDUMP | E1 contract/idempotent | FT-FC-CRASH, FT-HC-GENERIC, FT-OPS-BACKUP |
| R2 egress injection | FT-CL-ENV/HEADER/EXCHANGE | E2 durable store | FT-FC-CRASH, FT-OPS-*, FT-DK-SINGLEWRITER |
| R3 bindings | FT-BR-* | E3 single-use | FT-BR-*, FT-RK-INFLIGHT, FT-SU-* |
| R4 revoke ≤1s | FT-RK-KILLTIME/SCOPE/INFLIGHT/ATTR | E4 fail-closed | FT-FC-*, FT-AG-OFFLINE, FT-AP-FLOOD |
| R5 backends fail-closed | FT-FC-LOCKED/ABSENT/CONFIG, FT-CL-ROTATE | E5 redaction | FT-LA-NOSECRET, FT-AP-EVIDENCE |
| R6 ledger/events | FT-LA-* | E6 time | FT-CL-TTL, FT-NFR-CLOCK |
| R7 evasion | FT-EV-* | E7 injection engine | FT-CL-ENV/HEADER/EXCHANGE, FT-AP-WIDEN |
| R8 stdio | FT-ST-*, FT-DK-BOUNDARY | E8 harness adapters | FT-HC-* |
| R9 step-up | FT-SU-* | E9 pluggable backends | FT-CONF-BACKENDS, FT-FC-LOCKED/ABSENT |
| R17 scan/migrate | FT-MP-SCANMIGRATE | E10 control plane | FT-AP-TAMPER, FT-DK-BOUNDARY, FT-OPS-SERVE |
| | | E11 versioning | FT-OPS-MIGRATE/BACKUP/RESTORE |
| | | E12 ledger/export/sink | FT-LA-*, FT-FC-SINK, FT-OPS-BACKUP |
| | | E13 conformance | FT-CONF-STANDARDS |
| | | E14 no passthrough | FT-ST-NOPASSTHRU, FT-CL-HEADER |
| | | E15 supply chain | FT-SC-INREPO (signing = M15) |

### CUJs (PRD 04)

| CUJ | Cases |
|---|---|
| 1 first call <15 min | FT-CL-FIRST, FT-MP-SCANMIGRATE, FT-CL-ENV, FT-DK-QUICKSTART |
| 2 revoke ≤1s | FT-RK-KILLTIME/SCOPE/INFLIGHT/ATTR |
| 3 context-dump zero | FT-AP-CONTEXTDUMP, FT-AP-EVIDENCE |
| 4 stdio no secret | FT-ST-NOSECRET/NOPASSTHRU, FT-DK-BOUNDARY |
| 5 binding replay fails | FT-BR-* |
| 6 evasion caught | FT-EV-* |
| 7 step-up | FT-SU-* |
| 8 fail-closed day | FT-FC-*, FT-OPS-DOCTOR |
| 9 audit reconstruction | FT-LA-*, FT-OPS-BACKUP/RESTORE |
| 10 rotate without restart | FT-CL-ROTATE |
| 11 air-gap | FT-AG-OFFLINE, FT-DK-AIRGAP, FT-NFR-PORT |
| 12 two harnesses | FT-CL-TWOHARNESS, FT-HC-* |
| 13 embed the broker | FT-HC-GENERIC, FT-CONF-BACKENDS, FT-BR-* |
| 14 enterprise honesty | FT-HC-NOTYET, FT-SC-INREPO, FT-HONESTY-* |

### Invariants, risks, decisions, STRIDE

| I# (PRD 06 §1) | Cases | Risk (PRD 08) | Cases | Decision (PRD 11) | Cases |
|---|---|---|---|---|---|
| I1 never-in-context | FT-AP-CONTEXTDUMP, FT-ST-NOSECRET | R-1 broker compromise | FT-AP-TAMPER/WIDEN/FLOOD | D-01 broker not vault | FT-FC-*, FT-AP-EVIDENCE |
| I2 fail closed | FT-FC-*, FT-AP-FLOOD | R-2 stdio runtime | FT-DK-BOUNDARY | D-02 no long-lived | FT-CL-TTL, FT-BR-STALE |
| I3 revoke unconditional | FT-RK-*, FT-SU-DENIED | R-3 fail-useless | FT-OPS-DOCTOR, FT-FC-* | D-03 below harness | FT-HC-*, FT-CL-TWOHARNESS |
| I4 single-use bound | FT-BR-* | R-4 MCP step-change | FT-CONF-STANDARDS | D-04 references loggable | FT-AP-CONTEXTDUMP |
| I5 no passthrough | FT-ST-NOPASSTHRU, FT-CL-HEADER | R-5 incumbents | FT-CL-FIRST | D-05 three drivers | FT-CL-* egress |
| I6 outside control plane | FT-AP-TAMPER, FT-DK-BOUNDARY, FT-OPS-SERVE | R-6 absorption | FT-ST-*, FT-RK-KILLTIME | D-06 fail closed | FT-FC-*, FT-AG-OFFLINE |
| I7 redaction | FT-LA-NOSECRET, FT-AP-EVIDENCE | R-7 adoption friction | FT-MP-SCANMIGRATE, FT-CL-FIRST | D-07 revoke unconditional | FT-RK-* |
| I8 tamper-evident | FT-LA-TAMPER, FT-OPS-RESTORE | R-8 standards drift | FT-CONF-STANDARDS | D-08 single writer | FT-OPS-SERVE, FT-DK-SINGLEWRITER |
| I9 time cannot be gamed | FT-CL-TTL, FT-NFR-CLOCK | R-9 supply chain | FT-SC-INREPO, FT-DK-IMAGE | D-09 hash chain | FT-LA-TAMPER |
| I10 supply chain | FT-SC-INREPO, FT-DK-IMAGE | R-10 over-claiming | FT-HONESTY-GAPS | D-10 step-up via policy | FT-SU-* |
| | | R-11 store corruption | FT-LA-TAMPER, FT-OPS-RESTORE, FT-FC-STORE | D-11 stdio boundary | FT-DK-BOUNDARY |
| | | R-12 bus factor | review log + report reviewer line | D-12 local-first | FT-AG-OFFLINE, FT-DK-AIRGAP |
| | | | | D-13 additive contracts | FT-OPS-MIGRATE |
| **STRIDE** (PRD 06 §2) | Cases | | | D-14 no passthrough | FT-ST-NOPASSTHRU |
| Spoofing | FT-AP-TAMPER (spoofed reference), FT-BR-* (rogue resolve refused) | | | D-15 DPoP deferred | FT-CONF-STANDARDS |
| Tampering | FT-AP-TAMPER, FT-LA-TAMPER, FT-FC-CONFIG | | | D-16 cloud backends deferred | FT-AG-OFFLINE, FT-FC-ABSENT |
| Repudiation | FT-RK-ATTR, FT-LA-EVENT (attribution on every event) | | | D-17 shared sessions | FT-BR-SESSION, FT-CL-TWOHARNESS |
| Info disclosure | FT-AP-CONTEXTDUMP, FT-AP-EVIDENCE, FT-LA-NOSECRET | | | | |
| DoS | FT-AP-FLOOD | | | | |
| Elevation | FT-SU-DENIED (no approval → no prod mint), FT-AP-WIDEN | | | | |

## 6. Blocking & flagship case specs

Each case: **Steps · Assert · Artifacts · Fail condition**. Assertions are machine-checkable (exit codes,
ledger queries, JSON fields).

### FT-RK-KILLTIME (SC-24) — the one-second kill

- **Steps:** in the broker container, for each scope (`session`, `agent`, `all`):
  `python -m agentkeys.bench.killtime --iterations 100`; then one `agentkeys replay --last` per scope.
- **Assert:** `p95_ms <= 1000` **and** `max_ms <= 1000` for every scope; `replay_failures == iterations`;
  every replay `REFUSED`; `revoked` carries the operator principal.
- **Artifacts:** `results/FT-RK-KILLTIME/{summary.json,env.json,commands.log}`; the published copy in
  `bench/results/`.
- **Fail:** any single max over budget — a max is not an average to hide ([PRD 17 §15](../../prd/17-scenarios.md)).

### FT-AP-CONTEXTDUMP (SC-40) — zero usable credentials

- **Steps:** build every variant (env / header / exchange egress; monitor / enforce; two harnesses;
  air-gap) from the transcript, tool args, process env, config files, generated code, logs, and the export.
  Scan with (a) the shape scanner and (b) the **resolves?** check. Run the seeded falsification control.
- **Usable, defined** ([PRD 21 §3](../../prd/21-evidence-register-and-method.md)): matches a credential
  shape **and** authenticates to a target or is a raw backend secret. A reference is **not** usable; a
  clearly-fake test value is not usable.
- **Assert:** 0 usable in every variant; references and fake values only; the seeded secret **is** flagged
  (a silent scanner is a harness failure).
- **Artifacts:** secret-free variant JSONs + the control result. The operator-cohort run is recorded
  separately, by hand.

### FT-AP-TAMPER (SC-41) — tamper against us fails closed

- **Steps:** flip the config to monitor; SIGKILL `serve` and probe the stale lock; resolve a spoofed
  `akref:` repeatedly (enumeration); rewrite a ledger row; attempt a store read from the child container.
- **Assert:** config mismatch → `tamper-detected` + `TamperError`; stale lock → `doctor` non-zero;
  spoof → `UnknownReference` + the enumeration signal at the threshold; ledger rewrite → `verify-log`
  exit `3` naming the seq. **No path mints a credential.**

### FT-AP-EVIDENCE (SC-43) — no secret material

- **Steps:** run a lifecycle + a redaction receipt; `scan_evidence`; seed a leak; repeat via the scan
  service over the broker volumes.
- **Assert:** clean run `ok == true`, `rows > 0`, `receipts >= 1`; seeded run `ok == false` naming the
  row; the export rendering is included in the scan.

### FT-MP-SCANMIGRATE (SC-51) — the adoption unlock

- **Steps:** scan the seeded corpus; migrate `GITHUB_TOKEN`; re-scan; attempt a migration into a locked
  backend; inject a rewrite failure; check broad reuse.
- **Assert:** 100% recall of planted sites; **0 printed values** across stdout/JSON/logs (string-search
  every planted value); broad reuse flagged; the value exists only in the `0600` backend; re-scan closes
  the finding; failed migrations leave every source file byte-identical.

### FT-ST-NOSECRET / FT-ST-NOPASSTHRU (SC-12/13) — the flagship

- **Steps:** `AGENTKEYS_SCOPED_TOKEN=akref:… agentkeys run --server <ref> -- <fixture child>`, with the
  fixture child in its own container (boundary) and once as a plain subprocess (documented co-located
  limitation); the child proves it received a token and calls the fake upstream; then send a client token
  in the child's request.
- **Assert:** authenticated; the child env holds the **token** (not the reference value, not the backend
  secret); the shape scanner finds 0 usable secrets in child config + env + transcript + parent env; the
  upstream receives the broker token and never the client token.

### FT-DK-BOUNDARY — the boundary is real

- **Steps:** from the child container, read the broker store volume, the credentials file, and the broker
  env.
- **Assert:** every read denied; the attempts recorded; the broker healthy; the only credential-shaped
  value the child holds is the scoped token. A readable boundary is a **FAIL** (R-2 tripwire).

### FT-AP-FLOOD — fail closed under load (STRIDE DoS)

- **Steps:** drive sustained resolution requests from the agent side; drive duplicate in-window requests;
  drive unknown-reference probes.
- **Assert:** every request is evaluated (no bypass under load); duplicate in-window requests return the
  same issuance (exactly-once); no failure path degrades to an allow or an unsafe default; the broker stays
  legible (`doctor` green after the flood).

## 7. Results, bench, and the report

```
field-test/v0.1.0/results/<case-id>/{summary.json,summary.md,env.json,commands.log}
field-test/v0.1.0/results/_bench/            # raw kill-time + context-dump JSON
field-test/v0.1.0/results/_setup/            # build/install/readiness logs
bench/                                       # the PUBLISHED pack (14.8):
  README.md            # exact re-run commands, pinned environment, hardware disclosure,
                       # how to file a divergent result (PRD 21 §6)
  results/*.json       # kill-time + context-dump, machine-readable
docs/field-test/v0.1.0/FIELD_TEST_REPORT.md  # HAND-MAINTAINED, verdicts entered by hand
```

**Report shape (the hand-written file):** the `HAND-MAINTAINED` marker; a verdict table with one row per
case (`case`, `scenario`, `verdict`, `limitation`, `evidence path`); the blocking-five up top; the
reviewer's name and date; the claims-label audit (every *field-tested* claim points at its row). Nothing
else writes it.

**Runner safety:** `run_pack.py` resolves every output path and **refuses** anything under
`docs/field-test/` or matching a `HAND-MAINTAINED` file; the guard test (`tests/test_field_report_guard.py`)
asserts the marker and the refusal.

```bash
# L0 regression
.venv/bin/python -m pytest
.venv/bin/python -m agentkeys conformance --json

# Docker topology (required)
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml up -d broker child upstream
python scripts/fieldtest/run_pack.py --pack docker

# Packs (inside the broker container)
python scripts/fieldtest/run_pack.py --pack core|binding|stdio|evasion|failclosed|audit|stepup|attack|migrate|ops|nfr|conformance

# Blocking measurements
python -m agentkeys.bench.killtime --iterations 100
python scripts/fieldtest/run_pack.py --pack killtime
python scripts/fieldtest/run_pack.py --pack attack --case FT-AP-CONTEXTDUMP
docker compose -f field-test/v0.1.0/docker/compose.yaml run --rm --network none airgap \
  python scripts/fieldtest/run_pack.py --pack offline

# Harness (WARN with evidence if absent)
python scripts/fieldtest/run_pack.py --pack harness

# Then: a human enters verdicts in FIELD_TEST_REPORT.md.
```

CI: L0 + kill-time stay in CI; M14 adds a `workflow_dispatch` leg that builds the topology, runs the packs,
and uploads `field-test/v0.1.0/results/`. It never writes the report.

## 8. Known limitations (the only reasons a WARN is allowed)

| Limitation | Case |
|---|---|
| No OS enforcer shipped; enforce blocks only where composed, else names the gap | FT-EV-ENFORCE |
| No Claude Code / Cursor on the box; the smoke is mandatory, the live run is declared | FT-HC-CLAUDE/CURSOR |
| No fresh field box for the timed <15-min run; the scripted quickstart still runs | FT-CL-FIRST |
| `migrate --backend keychain` not implemented; the `0600` file backend is used | FT-MP-SCANMIGRATE |
| The real-cohort context-dump needs humans; scripted variants are mandatory | FT-AP-CONTEXTDUMP |
| HTTP/exchange targets are fake services, not third-party APIs | FT-CL-HEADER/EXCHANGE |
| A co-located subprocess is not protectable; the container boundary is the tested shape, the co-located run is recorded as a limitation | FT-ST-NOSECRET, FT-DK-BOUNDARY |
| DPoP, cloud backends, fleet mode, posture, canaries | not scored |
| Signed release / SLSA / Scorecard | M15, not claimed here |

`WARN` is never allowed for SC-24/40/41/43/51.

## 9. Gates & issue map

- **M15 blocked** unless all five blocking cases PASS and no in-scope `P/F` case is FAIL or NOT RUN.
- **Labels** ([PRD 20 §6](../../prd/20-standards-and-claims.md)): *conformance* with a green suite;
  *field-tested* only with a hand-entered verdict; *verified* only after a third-party re-run of `bench/`.
- **Issues:** plan #172 · runner + Docker topology + cases.yaml #173 · core/binding #174 ·
  stdio/evasion/fail-closed #175 · kill-time #176 · context-dump #177 · report + guard #178 · harness #179 ·
  bench #180 · gates #181–#185.
