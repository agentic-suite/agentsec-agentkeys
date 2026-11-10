# Field-Test Plan — agentkeys v0.1.0

**Milestone:** M14 (#172–#185) · **Authored:** `14.D0` (#172), 2026-11-09 · **Plan →**
`docs/field-test/v0.1.0/FIELD_TEST_REPORT.md` (hand-maintained) · **Runner:** `scripts/fieldtest/run_pack.py`
+ `python -m agentkeys.fieldtest` · **Cases:** `field-test/v0.1.0/cases.yaml` · **Results:**
[`field-test/v0.1.0/results/`](../../../field-test/v0.1.0/results/) · **Docker:**
`field-test/v0.1.0/docker/` · **Bench:** `bench/`.

**BLUF.** Prove v0.1.0 on a real CLI, store, ledger, and container topology: agents hold references, the
broker injects scoped tokens at egress, `revoke` kills in ≤1s (replay-verified), a context dump finds zero
usable credentials, scan/migrate moves secrets out of `.env` with zero values printed, and tamper fails
closed. The matrix below is frozen; M14 is **running, not deciding**. Verdicts are entered **by hand** from
committed results — no automation writes the report ([PRD 21 §5](../../prd/21-evidence-register-and-method.md),
[AGENTS.md](../../../AGENTS.md)).

Sources: [WBS Part 8](../../wbs/v0.1.0/wbs-v0.1.0-part8-fieldtest-release.md) ·
[PRD 04](../../prd/04-users-and-cujs.md) · [PRD 05](../../prd/05-features.md) ·
[PRD 06](../../prd/06-security-baseline.md) · [PRD 07](../../prd/07-success-metrics.md) ·
[PRD 08](../../prd/08-risks.md) · [PRD 09](../../prd/09-roadmap.md) · [PRD 11](../../prd/11-decisions.md) ·
[PRD 12](../../prd/12-traceability.md) · [PRD 13](../../prd/13-non-functional-requirements.md) ·
[PRD 16](../../prd/16-adapters-and-integration.md) · [PRD 17](../../prd/17-scenarios.md) ·
[PRD 19](../../prd/19-harness-compatibility.md) · [PRD 20](../../prd/20-standards-and-claims.md) ·
[PRD 22](../../prd/22-operations-and-governance.md) · [PRD 23](../../prd/23-enterprise-adoption-and-hardening.md) ·
[honest gaps](../../explanation/honest-gaps.md).

---

## 1. Scope

**In scope:** SC-01–SC-43 + SC-51; features F1–F21; R1–R9 + R17; E1–E15; CUJ-1…CUJ-14; invariants I1–I10;
R-1…R-12; D-01…D-17; the ops surface (PRD 22); the standards suites (PRD 20).

**Out of scope, never scored:** SC-44–SC-50, SC-53 (forward slate); F22 `posture` (v0.1.x); F23 canaries
(P2); DPoP/RFC 9449; cloud backends; fleet/server mode; signed release + attestations (**M15**).

## 2. Rules

1. **No silent skips.** Every case is **PASS / FAIL / WARN / NOT RUN**. A `P/F` case that cannot run is a
   **FAIL of the run**. `WARN` only for the four `P/F|W` cases, with a named limitation in the report. `NOT
   RUN` on a blocking case blocks M15.
2. **Blocking:** SC-24 (kill-time), SC-40 (context-dump), SC-41 (tamper), SC-43 (evidence), SC-51
   (scan/migrate). `P/F` only — no WARN, no NOT RUN.
3. **Verify the verifier.** Blocking packs ship a falsification control (seeded secret/leak/broad-reuse). A
   silent scanner fails the run.
4. **Determinism.** No ML, no decision-affecting randomness, no network. The same pack reproduces its JSON
   except timings.
5. **No real secrets.** Fake fixtures only; the single live value is an operator throwaway token, never
   printed or committed.
6. **One harness.** The runner drives the shipped CLI, bench, evidence scanner, attack packs, invariants,
   conformance kit, ops module, and stdio wrapper. No parallel implementation.
7. **The report is hand-written.** `FIELD_TEST_REPORT.md` carries `HAND-MAINTAINED`; the guard test proves a
   writer refuses it. Automated drafts may write only `FIELD_TEST_REPORT.generated.md` and never overwrite a
   marked file.

## 3. Docker topology (reference environment)

```
docker network "fieldtest" (internal)
  broker      agentkeys serve/CLI, non-root, store volume 0600
  agent       field client + quickstart; no broker volume
  mcp-server  fixture stdio server; separate container = process boundary
  upstream    fake HTTP resource + fake RFC 8693 STS
  airgap      network_mode: none client
  secretscan  evidence scanner over the volumes
```

- Non-root everywhere; broker store `0600`; the agent container cannot read the store or socket.
- No network by default; only the fake upstream/STS are reachable. Air-gap uses `network_mode: none`.
- Pinned Python 3.12 slim base **by digest**, `TZ=UTC`, `LC_ALL=C`, `NO_COLOR=1`.
- Each result records image digests, OS/arch, python, git SHA, and the compose hash.
- The venv path runs the same packs when Docker is unavailable, except `FT-DK-*` (those require Docker).

## 4. Case matrix

`Env`: `ci` = no network/harness; `file` = file backend; `docker` = topology; `harness` = Tier-1 harness;
`human` = field box / operator cohort. `Class`: `P/F`, or `P/F|W` (WARN with §8 limitation).

### Core lifecycle (SC-01–07)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-CL-FIRST | SC-01 | install → first brokered call <15 min, no code change | human,docker | P/F\|W |
| FT-CL-ENV | SC-02 | env injection; 0 secret bytes in transcript/args | ci,file | P/F |
| FT-CL-HEADER | SC-03 | header injection; client token absent upstream | ci,docker | P/F |
| FT-CL-EXCHANGE | SC-04 | RFC 8693; audience==target, scope==tool, `act` present | ci,docker | P/F |
| FT-CL-TTL | SC-05 | expiry fires exactly once; no post-TTL use | ci | P/F |
| FT-CL-ROTATE | SC-06 | rotation picked up without restart | ci,file | P/F |
| FT-CL-TWOHARNESS | SC-07 | two sessions, one reference; one revoke kills both | ci | P/F |

### Binding / replay (SC-08–11)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-BR-AUDIENCE | SC-08 | wrong audience refused + `exchange-rejected` | ci | P/F |
| FT-BR-TOOL | SC-09 | wrong tool/scope refused | ci | P/F |
| FT-BR-SESSION | SC-10 | replay after session end refused | ci | P/F |
| FT-BR-STALE | SC-11 | stale/forwarded/widened all refuse | ci | P/F |

### stdio (SC-12–13)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-ST-NOSECRET | SC-12 | child authenticates; config/env/transcript hold 0 usable secrets | ci,docker | P/F |
| FT-ST-NOPASSTHRU | SC-13 | upstream gets broker token, never the client token | ci,docker | P/F |

### Evasion (SC-14–17)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-EV-DOTENV | SC-14 | `.env` read → high `evasion-detected` | ci,docker | P/F |
| FT-EV-CLOUD | SC-15 | cloud credential file read caught, path named | ci | P/F |
| FT-EV-KEYCHAIN | SC-16 | keychain read caught, attributed | ci | P/F |
| FT-EV-ENFORCE | SC-17 | blocked only where an enforcer composes; else gap named | ci | P/F\|W |

### Fail-closed (SC-18–23)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-FC-LOCKED | SC-18 | locked backend → deny, no fallback | ci | P/F |
| FT-FC-ABSENT | SC-19 | absent backend → deny | ci | P/F |
| FT-FC-CONFIG | SC-20 | ambiguous config → loud refusal | ci | P/F |
| FT-FC-STORE | SC-21 | corrupt store → no issuance; `doctor` non-zero | ci | P/F |
| FT-FC-SINK | SC-22 | sink offline → one `sink-gap`; chain intact | ci | P/F |
| FT-FC-CRASH | SC-23 | kill -9 mid-issue → recover, exactly-once | ci,docker | P/F |

### Revocation / kill-time (SC-24–28)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-RK-KILLTIME | **SC-24** | N≥100/scope; **p95 ≤1s AND max ≤1s**; replay refused | ci,docker,mac,lin | **P/F** |
| FT-RK-SCOPE | SC-25 | scoped revoke does not over-kill | ci | P/F |
| FT-RK-INFLIGHT | SC-26 | in-flight call's next hop fails | ci | P/F |
| FT-RK-UNKNOWN | SC-27 | unknown target → non-zero, named | ci | P/F |
| FT-RK-ATTR | SC-28 | `revoked` carries operator identity | ci | P/F |

### Lifecycle audit (SC-29–32)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-LA-EXPORT | SC-29 | ordered timeline + chain; joins by `session_id` | ci,docker | P/F |
| FT-LA-TAMPER | SC-30 | rewritten/deleted row detected, seq named | ci | P/F |
| FT-LA-NOSECRET | SC-31 | 0 usable secrets in the export | ci | P/F |
| FT-LA-EVENT | SC-32 | one event per transition with `event_version` | ci | P/F |

### Step-up (SC-33–34)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-SU-APPROVED | SC-33 | no mint before approval; provenance recorded; retry not re-asked | ci | P/F |
| FT-SU-DENIED | SC-34 | deny/timeout/self-approval mint nothing | ci | P/F |

### Harness compatibility (SC-35–38)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-HC-CLAUDE | SC-35 | Claude Code recipe → authenticated call; transcript only reference | harness | P/F\|W |
| FT-HC-CURSOR | SC-36 | Cursor recipe → authenticated call; same wrapper | harness | P/F\|W |
| FT-HC-GENERIC | SC-37 | generic MCP/SDK issue-use-revoke | ci | P/F |
| FT-HC-NOTYET | SC-38 | uncovered harness labelled not-yet, gap named | ci | P/F |

### Air-gap (SC-39)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-AG-OFFLINE | SC-39 | resolve/use/revoke with sockets off; cloud backend refuses | ci,docker | P/F |

### Attack packs (SC-40–43)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-AP-CONTEXTDUMP | **SC-40** | 0 usable creds every variant; seeded control fires | ci,docker,human | **P/F** |
| FT-AP-TAMPER | **SC-41** | config edit, kill, spoof, ledger rewrite all deny + event | ci,docker | **P/F** |
| FT-AP-WIDEN | SC-42 | widening refused at the binding | ci | P/F |
| FT-AP-EVIDENCE | **SC-43** | 0 secrets in store/export/ledger; seeded leak fails; receipts | ci,docker | **P/F** |

### Migration (SC-51)

| ID | SC | Check | Env | Class |
|---|---|---|---|---|
| FT-MP-SCANMIGRATE | **SC-51** | 100% recall, 0 printed; rewrite every site; rollback; re-scan clean | ci | **P/F** |

### Docker topology

| ID | Check | Env | Class |
|---|---|---|---|
| FT-DK-IMAGE | broker image non-root, pinned, secret-free; `doctor` green | docker | P/F |
| FT-DK-COMPOSE | broker/mcp/upstream healthy; store `0600` | docker | P/F |
| FT-DK-QUICKSTART | quickstart inside the **agent** container authenticates | docker | P/F |
| FT-DK-STDIO | stdio server in its own container; 0 secret in config/env/transcript | docker | P/F |
| FT-DK-ISO | agent/mcp containers cannot read broker store/socket; attempts logged | docker | P/F |
| FT-DK-AIRGAP | `--network none` run passes core + revoke | docker | P/F |
| FT-DK-EVIDENCE | evidence sidecar: 0 secrets; seeded leak fails | docker | P/F |

### Operations (M12 / PRD 22)

| ID | Check | Env | Class |
|---|---|---|---|
| FT-OPS-SERVE | live lock refuses a second broker; stale reported; SIGTERM cleans up | ci,docker | P/F |
| FT-OPS-BACKUP | WAL-safe backup, manifest, verified chain head, `0600` | ci | P/F |
| FT-OPS-RESTORE | tampered backup/live lock/newer schema refused; chain preserved | ci | P/F |
| FT-OPS-MIGRATE | forward migrate; downgrade refuses loudly | ci | P/F |
| FT-OPS-DOCTOR | chain/lock/config-integrity checks, correct exit codes, <2s | ci | P/F |
| FT-OPS-DRILL | drill emits p50/p95/max; report verdict hand-entered | ci,docker | P/F |
| FT-OPS-RETENTION | prune appends a marker, deletes nothing | ci | P/F |

### NFRs (PRD 13)

| ID | Check | Env | Class |
|---|---|---|---|
| FT-NFR-INJECT | env/header <10 ms p99, exchange <50 ms p99 (measured or finding) | ci | P/F |
| FT-NFR-BACKEND | file <1 ms, keychain <5 ms p99 (measured or finding) | ci | P/F |
| FT-NFR-COLDSTART | broker cold start <200 ms p99 | ci | P/F |
| FT-NFR-LEDGER | ledger append <2 ms p99 | ci | P/F |
| FT-NFR-RSS | idle container RSS <50 MB | docker | P/F |
| FT-NFR-CLOCK | clock jump cannot extend/resurrect; expiry once | ci | P/F |
| FT-NFR-PORT | macOS + Linux; Windows labelled not-yet | mac,lin | P/F |
| FT-NFR-A11Y | `NO_COLOR`, `--json`, stable exit codes, UTC times, linear text | ci | P/F |

### Conformance, supply chain, honesty

| ID | Check | Env | Class |
|---|---|---|---|
| FT-CONF-STANDARDS | RFC 8693/8707/9700/9728/9068/7636 green; DPoP `not-supported` | ci | P/F |
| FT-CONF-BACKENDS | file/keychain admitted; a broken fake rejected | ci | P/F |
| FT-SC-INREPO | stdlib-only, `security.txt`, CI gates, SBOM, fuzz; signing = M15 | ci,docker | P/F |
| FT-HONESTY-GAPS | claims ≤ evidence; every limitation named | ci | P/F |
| FT-HONESTY-REPORT | `HAND-MAINTAINED` marker; writer refuses the canonical file | ci | P/F |

**Totals:** 44 scenario cases + 7 Docker + 7 ops + 8 NFR + 5 conformance/honesty = **71 cases**.
`P/F|W` = 4 · blocking = 5.

## 5. Coverage

### Features (PRD 05 §C)

| Feature | Cases |
|---|---|
| F1 reference + migration helper | FT-MP-SCANMIGRATE, FT-CL-FIRST |
| F2 env injector | FT-CL-ENV, FT-ST-NOSECRET |
| F3 header injector | FT-CL-HEADER, FT-HC-CURSOR |
| F4 exchange injector | FT-CL-EXCHANGE |
| F5 TTL/audience/tool/session minting | FT-CL-ENV, FT-BR-*, FT-CL-TTL |
| F6 revoke + kill-time | FT-RK-* |
| F7 keychain + file backends | FT-FC-LOCKED/ABSENT, FT-CONF-BACKENDS, FT-CL-ROTATE |
| F8 fail-closed + doctor | FT-FC-*, FT-OPS-DOCTOR, FT-DK-HEALTH (doctor in FT-DK-IMAGE) |
| F9 ledger + events | FT-LA-EVENT, FT-LA-TAMPER |
| F10 export + verify-log | FT-LA-EXPORT, FT-LA-NOSECRET, FT-LA-TAMPER |
| F11 evasion detect/enforce | FT-EV-* |
| F12 stdio virtualization | FT-ST-*, FT-DK-STDIO |
| F13 step-up | FT-SU-APPROVED/DENIED |
| F14 redactor + receipts | FT-LA-NOSECRET, FT-AP-EVIDENCE |
| F15 store + capabilities | FT-FC-CRASH, FT-OPS-* |
| F16 config model | FT-FC-CONFIG, FT-CL-FIRST, FT-OPS-DOCTOR |
| F17 harness recipes | FT-HC-* |
| F18 conformance kit | FT-CONF-* |
| F19 attack packs | FT-AP-*, FT-RK-* |
| F20 SDK/CLI contract | FT-HC-GENERIC, FT-LA-EXPORT |
| F21 scan/migrate | FT-MP-SCANMIGRATE |
| F22 posture (v0.1.x) | not scored — limitation |
| F23 canaries (P2) | not scored — limitation |

### Requirements (PRD 05 §A/§B)

| Req | Cases | Req | Cases |
|---|---|---|---|
| R1 reference-only | FT-CL-ENV, FT-ST-NOSECRET, FT-AP-CONTEXTDUMP | E1 contract/idempotent | FT-CL-ENV, FT-HC-GENERIC, FT-OPS-BACKUP |
| R2 egress injection | FT-CL-ENV/HEADER/EXCHANGE | E2 durable store | FT-FC-CRASH, FT-OPS-SERVE/BACKUP |
| R3 bindings | FT-BR-* | E3 single-use | FT-BR-*, FT-RK-INFLIGHT, FT-SU-* |
| R4 revoke ≤1s | FT-RK-KILLTIME/SCOPE/INFLIGHT/ATTR | E4 fail-closed | FT-FC-*, FT-AG-OFFLINE, FT-DK-AIRGAP |
| R5 backends fail-closed | FT-FC-LOCKED/ABSENT/CONFIG, FT-CL-ROTATE | E5 redaction | FT-LA-NOSECRET, FT-AP-EVIDENCE |
| R6 ledger/events | FT-LA-* | E6 time | FT-CL-TTL, FT-NFR-CLOCK |
| R7 evasion | FT-EV-* | E7 injection engine | FT-CL-ENV/HEADER/EXCHANGE, FT-AP-WIDEN |
| R8 stdio | FT-ST-*, FT-DK-STDIO | E8 harness adapters | FT-HC-* |
| R9 step-up | FT-SU-* | E9 pluggable backends | FT-CONF-BACKENDS, FT-FC-LOCKED/ABSENT |
| R17 scan/migrate | FT-MP-SCANMIGRATE | E10 control plane | FT-AP-TAMPER, FT-DK-ISO, FT-OPS-SERVE |
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
| 4 stdio no secret | FT-ST-NOSECRET/NOPASSTHRU, FT-DK-STDIO, FT-DK-ISO |
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

### Invariants, risks, decisions

| I# (§PRD 06) | Cases | Risk (§PRD 08) | Tripwire cases | Decision (§PRD 11) | Cases |
|---|---|---|---|---|---|
| I1 never-in-context | FT-AP-CONTEXTDUMP, FT-ST-NOSECRET | R-1 broker compromise | FT-AP-TAMPER/WIDEN | D-01 broker not vault | FT-FC-*, FT-AP-EVIDENCE |
| I2 fail closed | FT-FC-* | R-2 stdio runtime | FT-DK-STDIO/ISO | D-02 no long-lived | FT-CL-TTL, FT-BR-STALE |
| I3 revoke unconditional | FT-RK-* | R-3 fail-useless | FT-OPS-DOCTOR, FT-FC-* | D-03 below harness | FT-HC-*, FT-CL-TWOHARNESS |
| I4 single-use bound | FT-BR-* | R-4 MCP step-change | FT-CL-ENV/HEADER/EXCHANGE, FT-CONF-STANDARDS | D-04 references loggable | FT-AP-CONTEXTDUMP |
| I5 no passthrough | FT-ST-NOPASSTHRU, FT-CL-HEADER | R-5 incumbents | FT-CL-FIRST | D-05 three drivers | FT-CL-* egress |
| I6 outside control plane | FT-AP-TAMPER, FT-DK-ISO | R-6 absorption | FT-ST-*, FT-RK-KILLTIME | D-06 fail closed | FT-FC-*, FT-AG-OFFLINE |
| I7 redaction | FT-LA-NOSECRET, FT-AP-EVIDENCE | R-7 adoption friction | FT-MP-SCANMIGRATE, FT-CL-FIRST | D-07 revoke unconditional | FT-RK-*, FT-SU-DENIED |
| I8 tamper-evident | FT-LA-TAMPER, FT-OPS-RESTORE | R-8 standards drift | FT-CONF-STANDARDS | D-08 single writer | FT-OPS-SERVE, FT-FC-CRASH |
| I9 time cannot be gamed | FT-CL-TTL, FT-NFR-CLOCK | R-9 supply chain | FT-SC-INREPO, FT-DK-IMAGE | D-09 hash chain | FT-LA-TAMPER |
| I10 supply chain | FT-SC-INREPO, FT-DK-IMAGE | R-10 over-claiming | FT-HONESTY-GAPS | D-10 step-up via policy | FT-SU-* |
| | | R-11 store corruption | FT-LA-TAMPER, FT-OPS-RESTORE | D-11 stdio boundary | FT-DK-STDIO/ISO |
| | | R-12 bus factor | review log + report | D-12 local-first | FT-AG-OFFLINE, FT-DK-AIRGAP |
| | | | | D-13 additive contracts | FT-OPS-MIGRATE |
| | | | | D-14 no passthrough | FT-ST-NOPASSTHRU |
| | | | | D-15 DPoP deferred | FT-CONF-STANDARDS |
| | | | | D-16 cloud backends deferred | FT-AG-OFFLINE, FT-FC-ABSENT |
| | | | | D-17 shared sessions | FT-BR-SESSION, FT-CL-TWOHARNESS |

## 6. Blocking & flagship case specs

### FT-RK-KILLTIME (SC-24) — the one-second kill

- **Steps:** in the broker container, for each scope (`session`, `agent`, `all`):
  `python -m agentkeys.bench.killtime --iterations 100`; then one `agentkeys replay --last` per scope.
- **Assert:** `p95_ms <= 1000` and `max_ms <= 1000` every scope; `replay_failures == iterations`; every replay
  `REFUSED`; `revoked` carries the operator.
- **Artifacts:** `results/FT-RK-KILLTIME/{summary.json,env.json,commands.log}`; published JSON in `bench/`.
- **Fail:** any max over budget.

### FT-AP-CONTEXTDUMP (SC-40) — zero usable credentials

- **Steps:** build every variant (env/header/exchange, monitor/enforce, two harnesses, air-gap) from transcript,
  args, env, config, logs, export; scan with the shape scanner and the "resolves?" check; run the seeded
  control.
- **Assert:** 0 usable in every variant; references/fake values only; the seeded secret **is** flagged.
- **Artifacts:** secret-free variant JSONs + control result. The human cohort run is recorded separately.

### FT-AP-TAMPER (SC-41)

- **Steps:** flip config → monitor; SIGKILL `serve`; spoof `akref:` repeatedly; rewrite a ledger row; attempt to
  read the store from the agent container.
- **Assert:** `tamper-detected` + `TamperError`; stale lock non-zero; `UnknownReference` + enumeration signal;
  `verify-log` exit 3 naming the seq; no credential minted.

### FT-AP-EVIDENCE (SC-43)

- **Steps:** run a lifecycle + receipt; `scan_evidence`; seed a leak; repeat via the `secretscan` sidecar.
- **Assert:** clean `ok, rows>0, receipts>=1`; seeded `ok=false` naming the row; export included.

### FT-MP-SCANMIGRATE (SC-51)

- **Steps:** scan the corpus; migrate `GITHUB_TOKEN`; re-scan; migrate into a locked backend; inject a rewrite
  failure; check broad reuse.
- **Assert:** 100% recall; **0 printed values**; broad reuse flagged; value only in the `0600` backend; re-scan
  closed; failed migrations leave files byte-identical.

### FT-ST-NOSECRET / FT-ST-NOPASSTHRU (SC-12/13)

- **Steps:** `AGENTKEYS_SCOPED_TOKEN=akref:… agentkeys run --server <ref> -- <fixture server>` with the fixture
  in its own container; child proves it received a token; child sends a client token.
- **Assert:** authenticated; 0 secret shapes in config/env/transcript; upstream sees the broker token, never the
  client token.

### FT-DK-ISO — the boundary is real

- **Steps:** from `agent` and `mcp-server`, read the broker store, socket, and env.
- **Assert:** every read denied; attempts recorded; broker healthy. A readable boundary is a **FAIL** (R-2).

## 7. Results & execution

```
field-test/v0.1.0/results/<case-id>/{summary.json,summary.md,env.json,commands.log}
field-test/v0.1.0/results/_bench/            # kill-time + context-dump JSON
field-test/v0.1.0/results/_setup/            # build/install/readiness logs
docs/field-test/v0.1.0/FIELD_TEST_REPORT.md  # HAND-MAINTAINED, hand-entered verdicts
```

```bash
# L0 regression
.venv/bin/python -m pytest
.venv/bin/python -m agentkeys conformance --json

# Docker topology
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml up -d broker mcp-server upstream
python scripts/fieldtest/run_pack.py --pack docker

# Packs (local or in the broker container)
python scripts/fieldtest/run_pack.py --pack core|binding|stdio|evasion|failclosed|audit|stepup|attack|migrate|ops|nfr|conformance

# Blocking measurements
python -m agentkeys.bench.killtime --iterations 100
python scripts/fieldtest/run_pack.py --pack killtime
python scripts/fieldtest/run_pack.py --pack contextdump
docker compose -f field-test/v0.1.0/docker/compose.yaml run --rm --network none airgap \
  python scripts/fieldtest/run_pack.py --pack offline

# Harness (WARN with evidence if absent)
python scripts/fieldtest/run_pack.py --pack harness

# Then: enter verdicts by hand in the report.
```

CI: Layer 0 + kill-time stay in CI; M14 adds a `workflow_dispatch` leg that builds the topology, runs the packs,
and uploads `field-test/v0.1.0/results/`. It never writes the report.

## 8. Known limitations (the only reasons a WARN is allowed)

| Limitation | Case |
|---|---|
| No OS enforcer shipped; enforce blocks only where composed, else names the gap | FT-EV-ENFORCE |
| No Claude Code / Cursor on the box; smoke is mandatory, live run declared | FT-HC-CLAUDE/CURSOR |
| `init`, `context-dump`, `scan-usable` are stubs; quickstart writes the config directly | FT-CL-FIRST |
| `migrate --backend keychain` not implemented; file backend used | FT-MP-SCANMIGRATE |
| Real-cohort context-dump needs humans | FT-AP-CONTEXTDUMP |
| HTTP/exchange targets are fake services | FT-CL-HEADER/EXCHANGE |
| Co-located same-runtime stdio is not protectable; Docker boundary is the tested shape | FT-DK-ISO |
| DPoP, cloud backends, fleet mode, posture, canaries | not scored |
| Signed release / SLSA / Scorecard | M15, not claimed here |

`WARN` is never allowed for SC-24/40/41/43/51.

## 9. Gates & issue map

- **M15 blocked** unless all five blocking cases PASS and no in-scope `P/F` case is FAIL/NOT RUN.
- **Labels:** conformance with a green suite; field-tested only with a hand-entered verdict; verified only after
  a third-party re-run of `bench/`.
- **Report guard:** marker + refusal test; automation writes only `.generated.md` and never a marked file.
- **Issues:** plan #172 · runner/Docker #173 · core/binding #174 · stdio/evasion/fail-closed #175 ·
  kill-time #176 · context-dump #177 · report #178 · harness #179 · bench #180 · gates #181–#185.
