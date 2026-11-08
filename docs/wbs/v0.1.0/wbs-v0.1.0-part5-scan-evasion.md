# WBS v0.1.0 — Part 5: Hygiene & Hardening (M8–M9)

**BLUF:** **M8 ships the adoption unlock** — `agentkeys scan` finds the candidate secrets an agent can read
(and never prints the value), and `agentkeys migrate` moves one to a backend and rewrites every use site to a
reference ([R17](../../prd/05-features.md)) — the feature that makes the [quickstart](../../tutorials/quickstart.md)
a 15-minute journey. **M9 hardens against evasion and tamper**: raw-credential reads outside the broker are
high-severity events ([R7](../../prd/05-features.md)), and the broker lives **outside the agent's control
plane** so tampering fails closed ([E10](../../prd/05-features.md)) — the "we are a target" posture of
[PRD 06 §3](../../prd/06-security-baseline.md).

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M8 — Secret-hygiene scan + migrate (R17)

**Goal:** find the secrets where agents can read them — `.env`, `mcp.json`, MCP configs, shell scripts,
exported env — **without ever printing a value**, and move one into a backend while rewriting every use site
to a reference. This is [CUJ-1](../../prd/04-users-and-cujs.md) end-to-end.

**CUJ:** [CUJ-1](../../prd/04-users-and-cujs.md) · **Requirements:** [R17](../../prd/05-features.md),
[R1](../../prd/05-features.md), [E1](../../prd/05-features.md), [PRD 16 §3](../../prd/16-adapters-and-integration.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 8.D0 | **Design docs first** | Scan classes + migrate flow + the safety rules (never print, no auto-migrate, leave-on-failure) | docs | reviewed before code | #101 | — | — |
| 8.1 | Scanner | Detect secret shapes (API keys, bearer, private keys, conn strings, cloud creds), config-embedded values, and **broad-reuse** (same secret across many sites) | scanner module | finds every planted candidate in the fixture corpus | #102 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md) |
| 8.2 | Masked preview + never-print rule | Output is a masked preview + file/field location only; a value never reaches stdout/logs | output module | 0 printed secret values across the corpus | #103 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md), [E5](../../prd/05-features.md) |
| 8.3 | `migrate` | Move the value to the chosen backend; rewrite every use site to an `akref:`; a failed migration leaves the original file untouched | migrate module | source file rewritten; value present nowhere except the backend | #104 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md) |
| 8.4 | Seeded fixture corpus + recall test | A repo with fake secrets across `.env`/`mcp.json`/script, one broad-reuse case; the recall + never-print assertions | fixtures | 100% recall; 0 printed; re-scan shows the finding closed | #105 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md) |
| 8.5 | `--json` / CI mode | Machine-readable scan output; CI mode stub (**scheduled for v0.1.x** per [PRD 05 R17](../../prd/05-features.md)) — honestly labeled "not yet" | CLI | `--json` stable; CI mode refused as not-yet | #106 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md) |
| 8.T | Tests | Scanner recall, never-print, migrate rewrite, failure-safety | tests | coverage ≥95% | #107 | — | — |
| 8.C | Coverage gate | ≥95% on scan/migrate modules | coverage report | ≥95% | #108 | — | — |
| 8.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #109 | — | — |
| 8.CR | Code review | Findings resolved | review log | no open findings | #110 | — | — |
| 8.D | Docs | [PRD 05 R17](../../prd/05-features.md); scan/migrate reference; quickstart tie-in; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #111 | — | — |
| 8.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 8.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] **100% recall** on the seeded corpus with **0 printed secret values** ([SC-51](../../prd/17-scenarios.md), release-blocking)
- [ ] Migrate moves a secret end-to-end and closes the finding; a failed migrate leaves the file untouched

**Planned (opens at `8.D0`).** Design: [`docs/design/v0.1.0/scan-migrate.md`](../../design/v0.1.0/) · Scenarios:
[SC-51](../../prd/17-scenarios.md) · Tests: `tests/test_scan_candidates.py`, `tests/test_migrate_flow.py`.

---

## Milestone M9 — Evasion detection + tamper resistance (R7, E10)

**Goal:** catch an agent (or a poisoned tool) reading a raw credential **outside the broker**, and make the
broker itself tamper-resistant — a separate process the agent cannot read, edit, or silently kill. Evasion is
a high-severity event; where an enforcer composes, the read is blocked, and where it cannot, the gap is
**named** ([PRD 06 §4](../../prd/06-security-baseline.md), [PRD 14 §2](../../prd/14-non-goals.md)).

**CUJ:** [CUJ-6](../../prd/04-users-and-cujs.md) · **Requirements:** [R7](../../prd/05-features.md),
[E10](../../prd/05-features.md), [E4](../../prd/05-features.md), [PRD 06 §3–§4](../../prd/06-security-baseline.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 9.D0 | **Design docs first** | Evasion paths per OS; the tamper model; the honest-gap rule ("never claim a block we can't do") | docs | reviewed before code | #112 | — | — |
| 9.1 | Evasion detector | Flag `.env` / cloud-cred-file / keychain reads outside the broker as **high-severity** events | detector module | the evasion pack is caught in monitor-safe mode | #113 | [CUJ-6](../../prd/04-users-and-cujs.md) | [R7](../../prd/05-features.md) |
| 9.2 | `evasion-detected` event | Emit the event with path, attribution, and severity; join to the ledger | events hook | event present with all fields | #114 | [CUJ-6](../../prd/04-users-and-cujs.md) | [R7](../../prd/05-features.md) |
| 9.3 | Enforce-mode hooks + honest gap | Where agentkernel/agentseatbelt compose, block-and-log; where not, record + **name the gap** | enforce hook | covered paths blocked+logged; uncovered recorded as a named gap | #115 | [CUJ-6](../../prd/04-users-and-cujs.md) | [R7](../../prd/05-features.md) |
| 9.4 | Control-plane separation + config integrity | Broker runs outside the agent's plane; config integrity checked at session start; tamper → fail closed + loud event | core module | tamper fixtures fail closed with an event | #116 | — | [E10](../../prd/05-features.md) |
| 9.5 | Tamper fixtures | Edit config to always-allow; kill the broker; spoof a reference; rewrite the ledger | fixtures | every path denies and emits an event ([SC-41](../../prd/17-scenarios.md)) | #117 | — | [E10](../../prd/05-features.md) |
| 9.6 | Reference-enumeration signal | Repeated unknown-reference probes are detectable as an evasion-class signal | detector | enumeration probe raises the signal | #118 | — | [E10](../../prd/05-features.md) |
| 9.T | Tests | Evasion detect/enforce, tamper, enumeration | tests | coverage ≥95% | #119 | — | — |
| 9.C | Coverage gate | ≥95% on evasion/tamper modules | coverage report | ≥95% | #120 | — | — |
| 9.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #121 | — | — |
| 9.CR | Code review | Findings resolved | review log | no open findings | #122 | — | — |
| 9.D | Docs | [PRD 06 §3–§4](../../prd/06-security-baseline.md); evasion reference; runbook rb-3 seed; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #123 | — | — |
| 9.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 9.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Evasion caught in monitor-safe mode; blocked-where-composed; gaps named ([SC-14–SC-17](../../prd/17-scenarios.md))
- [ ] **Tamper against us fails closed** ([SC-41](../../prd/17-scenarios.md), release-blocking)

**Planned (opens at `9.D0`).** Design: [`docs/design/v0.1.0/evasion-tamper.md`](../../design/v0.1.0/) · Scenarios:
[SC-14–SC-17](../../prd/17-scenarios.md), [SC-41](../../prd/17-scenarios.md) · Tests:
`tests/test_evasion_detect.py`, `tests/test_evasion_enforce.py`, `tests/test_tamper_config.py`, `tests/test_tamper_broker.py`.

---

Part 5 green ⇒ users can migrate in minutes and the broker resists evasion/tamper; proceed to
[Part 6 (M10–M11)](wbs-v0.1.0-part6-stepup-conformance.md).
