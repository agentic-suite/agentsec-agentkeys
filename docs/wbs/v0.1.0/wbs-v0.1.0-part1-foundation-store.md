# WBS v0.1.0 — Part 1: Foundation & BrokerStore (M0–M1)

**BLUF:** **M0 builds the foundation fresh** (no predecessor to port): packaging as `agentsec-agentkeys`, the
CLI framework with **reserved exit codes**, the fail-closed config model (references only — a literal secret
is a lint error), CI quality gates, and `doctor`. **M1 delivers the pluggable BrokerStore contract (E2, E11)**
with SQLite (WAL, reference) + memory drivers — the durable truth layer every later milestone writes
through, proven by its own conformance suite before anything mints a credential on it.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M0 — Foundation & identity

**Goal:** agentkeys exists as an installable, CI-gated Python project with its full CLI surface, its reserved
exit codes (a compatibility contract the rest of the suite consumes), a fail-closed config model, and a
`doctor` skeleton. Nothing brokers yet — the skeleton is honest about that.

**CUJ:** — (foundation) · **Requirements:** [PRD 02](../../prd/02-architecture.md) (interfaces, exit codes),
[PRD 13](../../prd/13-non-functional-requirements.md) (performance, portability), [PRD 14](../../prd/14-non-goals.md)
(scope guard), [E4](../../prd/05-features.md), [E11](../../prd/05-features.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 0.D0 | **Design docs first** | Foundation design: CLI surface, exit-code contract, config model incl. `AGENTKEYS_HOME`, store layout sketch | docs | reviewed before code | #5 | — | — |
| 0.1 | Packaging + build | `pyproject.toml` for `agentsec-agentkeys` (dist) / `agentkeys` (package + console script); `make setup/lint/typecheck/test/cov/gate` | build config | `pip install -e .`; `make setup` green | #6 | — | [E15](../../prd/05-features.md) |
| 0.2 | CLI framework + command surface | Command skeleton: `init`, `doctor`, `scan`, `migrate`, `ref`, `run`, `revoke`, `replay`, `context-dump`, `scan-usable`, `export`, `verify-log`, `conformance`, `serve`, `version` — stubs that refuse honestly | CLI | `agentkeys --help` lists commands; stubs exit non-zero with a clear message | #7 | — | — |
| 0.3 | **Reserved exit codes** | Freeze the contract: `0` success/0-usable · `2` denied · `3` tamper · `4` revoke-verified · `1` usage/internal — documented + fixture-tested | exit-code module + fixtures | any command mapping a decision uses exactly these; fixture green | #8 | — | [PRD 15 §7](../../prd/15-data-model.md) |
| 0.4 | Configuration model | TOML load/validate ([PRD 15 §7](../../prd/15-data-model.md)): backends, `ttl.<class>.floor/ceiling`, bindings, `enforce_mode`, `sink`, `store.path`; **references only** (literal secret = lint error); `AGENTKEYS_HOME` override | config loader | invalid/ambiguous config fails closed with an actionable error; `doctor` explains the effective config | #9 | — | [E4](../../prd/05-features.md) |
| 0.5 | CI & quality gate | `ruff` + `mypy --strict` + `pytest` + coverage ≥95% + DCO check | GitHub Actions | CI green on a trivial PR | #10 | — | — |
| 0.6 | `doctor` skeleton | Checks store path/permissions, config validity, backend registry, schema version, clock — each exit-coded; grows in M3/M9/M12 | CLI | `doctor` returns 0 on a healthy fresh install, names failures otherwise | #11 | — | [E4](../../prd/05-features.md) |
| 0.7 | Identity & governance docs | README (the real one), LICENSE/CODEOWNERS/SECURITY/AGENTS/CONTRIBUTING finalized | docs | docs match the repo identity | #12 | — | — |
| 0.T | Tests | Config fail-closed, CLI smoke, exit-code fixtures, `doctor` | tests | all new paths covered; coverage ≥95% | #13 | — | — |
| 0.C | Coverage gate | Enforce ≥95% on this milestone's modules | coverage report | ≥95%; no untested new path | #14 | — | — |
| 0.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #15 | — | — |
| 0.CR | Code review | Findings in [codereview-log.md](codereview-log.md), resolved | review log | no open findings | #16 | — | — |
| 0.D | Docs | Foundation design + CLI reference start; [PRD 12](../../prd/12-traceability.md) rows wired | docs | docs updated + linked here | #17 | — | — |
| 0.CI | Commit & push | On the feature branch | git | pushed | — | — | — |
| 0.W | Update WBS | Checkpoint appended to the [index](wbs-v0.1.0-index.md) Progress | WBS | checkpoint recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · all tests pass · coverage ≥ 95% · lint strict clean · docs updated · committed+pushed
- [ ] `pip install -e .` + `make` targets work; `agentkeys --help` lists the full surface
- [ ] Reserved exit codes frozen + fixture-tested; bad config fails closed; CI green

**Planned (opens at `0.D0`).** Design: [`docs/design/v0.1.0/foundation.md`](../../design/v0.1.0/) · Reference:
[`docs/reference/cli.md`](../../reference/cli.md), [`docs/reference/glossary.md`](../../reference/glossary.md).

---

## Milestone M1 — BrokerStore contract + drivers (E2, E11)

**Goal:** define the **only** way the core touches state — the typed BrokerStore interface with its hard
semantics (idempotent issue, CAS on revocation, atomic single-use consumption, durable-commit-before-ack,
exactly-once recovery, capability flags) — and implement **SQLite (WAL, reference)** and **memory** drivers,
both passing the conformance suite. Future drivers inherit this contract instead of re-deriving semantics
([PRD 15 §5–§6](../../prd/15-data-model.md)).

**CUJ:** — (infrastructure) · **Requirements:** [E2](../../prd/05-features.md), [E11](../../prd/05-features.md),
[PRD 15 §5–§7](../../prd/15-data-model.md), [PRD 13](../../prd/13-non-functional-requirements.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 1.D0 | **Design docs first** | Store design: the typed interface, the semantics, schema DDL (references/sessions/bindings/issuances/revocations/ledger), migration/version table, capability-flag selection | docs | reviewed before code | #18 | — | — |
| 1.1 | BrokerStore interface | `create_reference`, `get`, `issue`/`get_issuance`, `consume`, `cas_revoke`, `list_live`, `append_event`, `export_session` + flags (`single_writer`, `durable`, `atomic_issue`, `cluster_safe`) | interface module | mypy-clean protocol; fail-closed capability check helper | #19 | — | [E2](../../prd/05-features.md), [E11](../../prd/05-features.md) |
| 1.2 | SQLite driver (reference) | WAL, fsync'd commits, 0600 store / 0700 dir defaults, indexes (issuances-by-binding, by-session, ledger-by-seq, live-by-expiry) | driver | all semantics fixtures pass | #20 | — | [E2](../../prd/05-features.md) |
| 1.3 | Memory driver | Same semantics, no disk — for tests/embedded ephemeral use | driver | same fixtures pass (both drivers share the suite) | #21 | — | [E2](../../prd/05-features.md) |
| 1.4 | **Store conformance suite** | The semantics as fixtures: idempotent issue per binding+window, CAS revoke (exactly one winner, epoch monotonic), single-use consume, gapless ledger seq, exactly-once recovery, durable-commit-before-ack (crash mid-write), capability refusal | fixtures | both drivers green; a deliberately broken fake driver **fails** the suite | #22 | — | [E2](../../prd/05-features.md), [E12](../../prd/05-features.md) |
| 1.5 | Schema versioning + migrations | Version table; forward migrations on open; **downgrade refuses loudly**; migration tested old→new | migration module | old-store fixture opens and migrates; downgrade exits non-zero | #23 | — | [E11](../../prd/05-features.md) |
| 1.6 | Driver selection + entry points | `agentkeys.store` entry points for third-party drivers; unconformant/unlisted drivers refuse to load with a clear error | loader | a fake third-party driver loads only when it passes conformance | #24 | — | [E9](../../prd/05-features.md) |
| 1.T | Tests | Driver units + the conformance suite run against both drivers | tests | coverage ≥95% | #25 | — | — |
| 1.C | Coverage gate | Enforce ≥95% on store modules | coverage report | ≥95% | #26 | — | — |
| 1.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #27 | — | — |
| 1.CR | Code review | Findings resolved | review log | no open findings | #28 | — | — |
| 1.D | Docs | Store reference (semantics + DDL + capability flags); conformance-suite doc for driver authors | docs | docs updated + linked | #29 | — | — |
| 1.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 1.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] The BrokerStore interface is the only state path; both drivers pass the full conformance suite
- [ ] Capability-mismatched configs refuse to start; downgrade refuses loudly; store perms correct by default

**Planned (opens at `1.D0`).** Design: [`docs/design/v0.1.0/store.md`](../../design/v0.1.0/) · Reference:
[`docs/reference/cli.md`](../../reference/cli.md) · Scenarios: [SC-21/SC-23](../../prd/17-scenarios.md).

---

Part 1 green ⇒ the truth layer exists and is proven; proceed to
[Part 2 (M2–M3)](wbs-v0.1.0-part2-contracts-backends.md).
