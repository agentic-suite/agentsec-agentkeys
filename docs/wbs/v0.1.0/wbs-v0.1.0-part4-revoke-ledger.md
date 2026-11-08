# WBS v0.1.0 — Part 4: Revocation & Evidence (M6–M7)

**BLUF:** **M6 ships the number the product is judged on** — `revoke` end-to-end **≤1s**, replay-verified,
with time correctness so a clock jump cannot game a TTL ([R4](../../prd/05-features.md),
[E6](../../prd/05-features.md)). **M7 turns every lifecycle transition into evidence**: the append-only,
hash-chained **ledger**, the **agentwatch** event set, and `export` / `verify-log`
([R6](../../prd/05-features.md), [E12](../../prd/05-features.md)) — the artifact an auditor (and
agentcomply) consumes.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M6 — Revocation + kill-time ≤1s + time correctness (R4, E6)

**Goal:** one command kills all of an agent's access in ≤1s, proven by replay, not by a status flag. Revoke
is a CAS on the session `revoke_epoch` ([PRD 18 §7](../../prd/18-issuance-integrity.md)); the kill is
measured end-to-end and runs in CI. Time correctness makes a clock jump unable to extend a TTL.

**CUJ:** [CUJ-2](../../prd/04-users-and-cujs.md) (the spine) · **Requirements:**
[R4](../../prd/05-features.md), [E6](../../prd/05-features.md), [E3](../../prd/05-features.md),
[PRD 18 §7](../../prd/18-issuance-integrity.md), [PRD 07 §2.1](../../prd/07-success-metrics.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 6.D0 | **Design docs first** | Revoke-epoch design; the kill-time protocol (t0→replay-fails t1); time-correctness rules | docs | reviewed before code | #77 | — | — |
| 6.1 | `revoke <agent\ | session\ | all>` | CAS on `revoke_epoch`; next exchange refuses; issued tokens stop authenticating; attribution recorded | #78 | scoped kills don't over-kill; `--all` explicit | #TBD | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 6.2 | **Kill-time harness** | Issue → revoke → tight-loop replay until refusal; N≥100 per scope; p50/p95/max; runs **in CI** | bench + test | p95 ≤1s **and** max ≤1s | #79 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 6.3 | `replay` command + refusal evidence | Re-issue the last pre-revoke attempt; a `REFUSED (exchange-rejected)` exit `4` is the proof | CLI | replay of a killed credential fails; exit code stable | #80 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 6.4 | Scoped revoke + unknown target | `--agent`/`--session` kill only the target; unknown target is a loud error, never a silent no-op | CLI | SC-25/SC-27 pass | #81 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 6.5 | Time correctness | UTC absolute instants + monotonic deltas; backwards jump cannot extend, forwards cannot resurrect | time module | clock-skew fixtures behave fail-closed; expiry fires once | #82 | — | [E6](../../prd/05-features.md) |
| 6.6 | `revoked` event + attribution | Event carries scope, target, operator principal, `effective_at` measured vs the ≤1s budget | events hook | SC-28 passes | #83 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 6.T | Tests | Kill-time, scope, time correctness, in-flight | tests | coverage ≥95% | #84 | — | — |
| 6.C | Coverage gate | ≥95% on revoke/time modules | coverage report | ≥95% | #85 | — | — |
| 6.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #86 | — | — |
| 6.CR | Code review | Findings resolved | review log | no open findings | #87 | — | — |
| 6.D | Docs | [PRD 18 §7](../../prd/18-issuance-integrity.md); kill-time protocol; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #88 | — | — |
| 6.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 6.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Kill-time **≤1s** end-to-end in CI ([SC-24](../../prd/17-scenarios.md), release-blocking)
- [ ] Scoped revoke never over-kills ([SC-25](../../prd/17-scenarios.md)); unknown target errors loudly ([SC-27](../../prd/17-scenarios.md))
- [ ] No clock path can extend or resurrect ([SC-05](../../prd/17-scenarios.md))

**Planned (opens at `6.D0`).** Design: [`docs/design/v0.1.0/revoke.md`](../../design/v0.1.0/) · Scenarios:
[SC-24–SC-28](../../prd/17-scenarios.md), [SC-05](../../prd/17-scenarios.md) · Tests:
`tests/test_revoke_killtime.py`, `tests/test_revoke_scope.py`, `tests/test_time_correctness.py`.

---

## Milestone M7 — Lifecycle ledger + agentwatch events + export/verify-log (R6, E12)

**Goal:** every issuance, use, upgrade, revocation, rejection, and evasion is an append-only, **hash-chained**
ledger entry and an **agentwatch-schema** event ([PRD 15 §4](../../prd/15-data-model.md)) — a credential
lifecycle an auditor reconstructs per session and a tamper test cannot silently alter.

**CUJ:** [CUJ-9](../../prd/04-users-and-cujs.md) · **Requirements:**
[R6](../../prd/05-features.md), [E12](../../prd/05-features.md), [E5](../../prd/05-features.md),
[PRD 15 §4–§5](../../prd/15-data-model.md), [PRD 02 §7](../../prd/02-architecture.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 7.D0 | **Design docs first** | Ledger design (`seq`/`prev_hash`/`hash`), the event set + `event_version`, export format, join keys | docs | reviewed before code | #89 | — | — |
| 7.1 | Hash-chained ledger | Append-only rows; `hash = H(canonical(row) ‖ prev_hash)`; genesis anchor; no update/delete | ledger module | chain verifies; a rewritten row is detected | #90 | [CUJ-9](../../prd/04-users-and-cujs.md) | [R6](../../prd/05-features.md) |
| 7.2 | agentwatch event emitter | The lifecycle event set (`reference-resolved`, `issued`, `use`, `exchange-rejected`, `step-up-*`, `evasion-detected`, `revoked`, `expired`) with `event_version` | events module | one event per transition; schema fixtures with allow-lists | #91 | [CUJ-9](../../prd/04-users-and-cujs.md) | [R6](../../prd/05-features.md) |
| 7.3 | `export --session/--reference` | Deterministic ordered JSONL (principal, binding, timestamps, reasons, chain); 0600; audited | CLI | reconstruction per session; joins to the trace by `session_id` | #92 | [CUJ-9](../../prd/04-users-and-cujs.md) | [R6](../../prd/05-features.md) |
| 7.4 | `verify-log` | Recompute the chain; report integrity, gaps, first bad seq; read-only (no migration) | CLI | a tampered or reordered row is detected, not skipped | #93 | [CUJ-9](../../prd/04-users-and-cujs.md) | [E12](../../prd/05-features.md) |
| 7.5 | Join keys + trace correlation | `session_id`/`agent_id`/`reference_id`/`issuance_id` join ledger ↔ agentwatch ↔ session trace | correlation module | an audit joins lifecycle to session trace | #94 | [CUJ-9](../../prd/04-users-and-cujs.md) | [R6](../../prd/05-features.md) |
| 7.6 | Sink adapter (buffered) | Ship events to the agentwatch sink; on outage the local ledger stays authoritative with a **gap marker** | sink module | sink offline → gap marker; nothing lost or silently allowed | #95 | — | [E12](../../prd/05-features.md) |
| 7.T | Tests | Chain, export, verify, correlation, sink-offline | tests | coverage ≥95% | #96 | — | — |
| 7.C | Coverage gate | ≥95% on ledger/event modules | coverage report | ≥95% | #97 | — | — |
| 7.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #98 | — | — |
| 7.CR | Code review | Findings resolved | review log | no open findings | #99 | — | — |
| 7.D | Docs | [PRD 15 §4–§5](../../prd/15-data-model.md); export/verify reference; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #100 | — | — |
| 7.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 7.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Full lifecycle reconstructable per session; the chain verifies; a tampered row is detected ([SC-29/SC-30](../../prd/17-scenarios.md))
- [ ] Export is secret-free by scan ([SC-31](../../prd/17-scenarios.md)); sink offline leaves the local ledger authoritative ([SC-22](../../prd/17-scenarios.md))

**Planned (opens at `7.D0`).** Design: [`docs/design/v0.1.0/ledger.md`](../../design/v0.1.0/) · Scenarios:
[SC-22](../../prd/17-scenarios.md), [SC-29–SC-32](../../prd/17-scenarios.md) · Tests:
`tests/test_ledger_chain.py`, `tests/test_export.py`.

---

Part 4 green ⇒ revocation is provable and every transition is evidence; proceed to
[Part 5 (M8–M9)](wbs-v0.1.0-part5-scan-evasion.md).
