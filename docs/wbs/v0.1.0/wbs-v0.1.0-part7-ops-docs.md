# WBS v0.1.0 — Part 7: Operations & Docs (M12–M13)

**BLUF:** **M12 makes the broker operable** — service units, backup/restore with ledger-chain continuity,
migration/downgrade behavior, `doctor` hardening, and the revoke-drill tooling ([PRD 22](../../prd/22-operations-and-governance.md)).
**M13 makes it explicable** — the reference every flag/key is coverage-tested against, the quickstart the
step test replays, the eight runbooks, and the harness recipes ([CUJ-1](../../prd/04-users-and-cujs.md),
[PRD 22](../../prd/22-operations-and-governance.md)). Docs are tested here, not hoped for.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M12 — Operations: service units, backup/restore, migrations, drills (PRD 22)

**Goal:** a credential broker is only as trustworthy as its **worst operational day**. Ship the ops surface
that makes a locked keychain, a corrupt store, a sink outage, and an upgrade day survivable — all fail-closed,
all legible, all recoverable without ever placing a literal secret back into a config
([PRD 22 §4–§6](../../prd/22-operations-and-governance.md)).

**CUJ:** [CUJ-8](../../prd/04-users-and-cujs.md) (fail-closed day), [CUJ-2](../../prd/04-users-and-cujs.md)
(drill) · **Requirements:** [R5](../../prd/05-features.md), [E4](../../prd/05-features.md),
[E12](../../prd/05-features.md), [PRD 22](../../prd/22-operations-and-governance.md),
[PRD 13](../../prd/13-non-functional-requirements.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 12.D0 | **Design docs first** | Ops surface design; backup format; restore/chain-continuity rules; service-unit shape (no root) | docs | reviewed before code | #148 | — | — |
| 12.1 | `serve` + service units | Long-lived broker process; user-scoped launchd/systemd units; SIGTERM flushes and closes cleanly | CLI + units | a dead `serve.lock` makes denial paths honest; no root required | #149 | — | [PRD 22 §2](../../prd/22-operations-and-governance.md) |
| 12.2 | Backup / restore | Online backup (WAL-safe) carrying **references only**; restore allow-lists extraction, verifies the chain, and never resurrects a decision | CLI | a restore with a chain mismatch is surfaced as tamper, not silently re-anchored | #150 | [CUJ-8](../../prd/04-users-and-cujs.md) | [E12](../../prd/05-features.md) |
| 12.3 | Migrations + downgrade refusal | Forward migrations on open; downgrade refuses loudly; every released schema migrates forward | migration module | old→new migration green; downgrade exits non-zero ([E11](../../prd/05-features.md)) | #151 | — | [E11](../../prd/05-features.md) |
| 12.4 | `doctor` hardening | Add backends, clock, chain, config-integrity, offline checks; stays <2s; explains the last denial | CLI | each check exit-coded; tamper/clock/config failures non-zero | #152 | [CUJ-8](../../prd/04-users-and-cujs.md) | [E4](../../prd/05-features.md) |
| 12.5 | Revoke-drill tooling | `replay`-based quarterly drill runner; machine-readable output for the hand-maintained report | tool | a drill produces p50/p95/max + pass/fail, entered by hand ([rb-7](../../prd/22-operations-and-governance.md)) | #153 | [CUJ-2](../../prd/04-users-and-cujs.md) | [R4](../../prd/05-features.md) |
| 12.6 | Retention + export policy | Local, append-only retention; pruning is a logged operation (a new event), never a silent delete; export path is secret-free | module | pruning emits a chain marker; export scanned clean | #154 | — | [E12](../../prd/05-features.md) |
| 12.T | Tests | Service lifecycle, backup/restore, migration, doctor, retention | tests | coverage ≥95% | #155 | — | — |
| 12.C | Coverage gate | ≥95% on ops modules | coverage report | ≥95% | #156 | — | — |
| 12.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #157 | — | — |
| 12.CR | Code review | Findings resolved | review log | no open findings | #158 | — | — |
| 12.D | Docs | [PRD 22](../../prd/22-operations-and-governance.md); ops reference; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #159 | — | — |
| 12.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 12.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] Backup/restore preserves chain continuity; a mismatch is surfaced as tamper ([PRD 22 §4](../../prd/22-operations-and-governance.md))
- [ ] Downgrade refuses loudly; the drill tooling produces the kill-time numbers; no ops step ever places a literal secret

**Planned (opens at `12.D0`).** Design: [`docs/design/v0.1.0/ops.md`](../../design/v0.1.0/) · Reference:
[PRD 22](../../prd/22-operations-and-governance.md) · Tests: `tests/test_serve_units.py`, `tests/test_backup_restore.py`,
`tests/test_schema_migration.py`, `tests/test_doctor_ops.py`.

---

## Milestone M13 — Docs completion: reference, quickstart, runbooks, recipes (PRD 22/13, CUJ-1)

**Goal:** every page a stranger needs to install, use, operate, and honestly evaluate v0.1.0 — and **docs are
tested**: the CLI/config coverage test fails on an undocumented flag or key, and the quickstart's exact
commands are replayed by a step test ([`docs/plans/docs-plan.md`](../../plans/docs-plan.md)).

**CUJ:** [CUJ-1](../../prd/04-users-and-cujs.md) · **Requirements:** [R17](../../prd/05-features.md),
[R5](../../prd/05-features.md), [PRD 22 §6](../../prd/22-operations-and-governance.md),
[PRD 13](../../prd/13-non-functional-requirements.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 13.D0 | **Design docs first** | Docs plan (exists: [`docs-plan.md`](../../plans/docs-plan.md)); page inventory finalized | docs | reviewed before code | #160 | — | — |
| 13.1 | CLI reference + coverage test | `docs/reference/cli.md`; a test walks the CLI parser so no flag ships undocumented | doc + test | coverage test green; a new flag without a doc row fails | #161 | — | [PRD 13](../../prd/13-non-functional-requirements.md) |
| 13.2 | Config reference + coverage test | `docs/reference/config.md`; every key documented and every documented key exists | doc + test | coverage test green both directions | #162 | — | [PRD 15 §7](../../prd/15-data-model.md) |
| 13.3 | Quickstart + step test | `docs/tutorials/quickstart.md`; the exact commands replayed through a pty, install → first brokered call (<15 min) | doc + test | step test completes; `tests/docs/test_quickstart.py` green | #163 | [CUJ-1](../../prd/04-users-and-cujs.md) | [R17](../../prd/05-features.md) |
| 13.4 | Runbooks rb-1..rb-8 | Symptoms → steps → verification for: locked backend, store corruption, suspected exfiltration, config drift, upgrade day, sink outage, revoke drill, secret rotation ([PRD 22 §6](../../prd/22-operations-and-governance.md)) | docs | each runbook's verification is executable/loggable | #164 | — | [PRD 22](../../prd/22-operations-and-governance.md) |
| 13.5 | Adapter recipes docs | The harness + generic recipes in [PRD 16](../../prd/16-adapters-and-integration.md) shipped under `docs/adapters/` | docs | each recipe ends in a verified call step | #165 | [CUJ-12](../../prd/04-users-and-cujs.md) | [E8](../../prd/05-features.md) |
| 13.6 | README + guides + enterprise honesty | Install/usage live; adoption-paths, demo-scripts, why-brokers-not-detectors; the honest gap page ([PRD 23](../../prd/23-enterprise-adoption-and-hardening.md)) | docs | no unsupported claim; links resolve | #166 | [CUJ-14](../../prd/04-users-and-cujs.md) | [PRD 23](../../prd/23-enterprise-adoption-and-hardening.md) |
| 13.T | Tests | CLI coverage, config coverage, quickstart step test, doc-link check | tests | coverage ≥95% | #167 | — | — |
| 13.C | Coverage gate | ≥95% on docs tests | coverage report | ≥95% | #168 | — | — |
| 13.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #169 | — | — |
| 13.CR | Code review | Findings resolved | review log | no open findings | #170 | — | — |
| 13.D | Docs | The pages themselves + [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #171 | — | — |
| 13.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 13.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] CLI + config coverage tests green (no undocumented flag/key; no documented-but-absent one)
- [ ] Quickstart step test completes install → first brokered call; runbooks + recipes + honesty page live

**Planned (opens at `13.D0`).** Design: [`docs/plans/docs-plan.md`](../../plans/docs-plan.md) · Reference:
[`docs/reference/cli.md`](../../reference/cli.md) · Tests: `tests/docs/test_cli_coverage.py`,
`tests/docs/test_doc_coverage.py`, `tests/docs/test_quickstart.py`.

---

Part 7 green ⇒ the broker is operable and documented; proceed to
[Part 8 (M14–M15)](wbs-v0.1.0-part8-fieldtest-release.md) — the final field test and release.
