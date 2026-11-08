# PRD 22 — Operations & Governance

**BLUF:** A credential broker is only as trustworthy as its **worst operational day**: the locked keychain
at 9 a.m., the corrupted store during an incident, the harness update that breaks a recipe, the revoked
agent whose tokens must be provably dead. This document is how agentkeys is **run**: install and
configuration-as-code, upgrade and migration policy, backup/restore with ledger-chain continuity, health
and monitoring (`doctor`, `verify-log`, posture), the **incident-response runbooks** (eight, each
symptom → steps → verification), the **revoke-drill program**, retention and export, and the governance
rules (config review, policy change via agentpolicy, evidence export for auditors). Everything here is
**local-first at v0.1.0**; server-mode ops (R11) extend, never replace, these semantics.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## 1. Deployment modes and their ops surface

| Mode | What runs | Ops surface | Status |
|---|---|---|---|
| **Local single-user** | One broker process + CLI + SQLite store + ledger, per developer/machine | This entire document | **v0.1.0** |
| **Air-gapped** | Local backends only; no sink, no network | Same, minus anything network-shaped; `doctor` confirms offline | v0.1.0 (CUJ-11) |
| **Embedded** (host product) | Broker as a library-driven subprocess via the SDK contract | The host owns lifecycle; the broker owns invariants | SDK contract (F20) |
| **Server / HA / fleet** | Central broker, cluster-safe store, delegation | Adds fleet ops: tenancy of *configs*, rolling upgrades, central revoke | **R11 — not yet** |

## 2. Install, init, and configuration-as-code

- `agentkeys init` writes a **single declarative config** (backends, TTL floors/ceilings per class,
  bindings, enforce mode, sink, store path — [PRD 15 §7](15-data-model.md)) and refuses to guess: partial
  or ambiguous config is a **startup failure**, not a default (E4).
- The config is **the** security surface: integrity-checked at session start; tamper → fail-closed + a loud
  event (E10). It is meant to live in the user's dotfiles/repo (no secrets in it by construction — only
  references and backend ids), so configuration review is a normal code review.
- `agentkeys doctor` is the first command of every runbook: it explains the **effective** backend, TTL
  bands, capability flags, clock state, and the *reason* for the most recent denial — read-only, never
  mints.

## 3. Upgrade, migration, and compatibility

- **Additive-only contracts** (E11): a 0.2.0 binary opens a 0.1.0 store by migrating forward, or
  **refuses loudly** — never silently rewrites. The reference grammar and event names are stable within
  v0.x.
- **Upgrade procedure:** stop broker → backup (§4) → install → `agentkeys doctor` → `verify-log` → start;
  the release notes carry the harness × version compatibility table **generated from CI**
  ([PRD 16 §7](16-adapters-and-integration.md)).
- **Recipe drift** is a first-class operational event: a harness update that breaks a recipe fails its
  agentdrill pack in CI — the fix is pin-or-update, never "works on my machine."

## 4. Backup, restore, and ledger continuity

| Object | What it is | Backup rule | Restore rule |
|---|---|---|---|
| Broker store | SQLite (WAL): sessions, bindings, issuances (hashed secrets only), revocations, ledger | File-level copy with the broker stopped (or the documented online snapshot) | Restore → `verify-log` must pass **before** the broker serves; chain mismatch = tamper posture, not "best effort" |
| Backends | The real secrets — **not ours to back up** | Your vault's own procedures (keychain sync, Vault replication) | Your vault's own procedures — the broker re-resolves by reference |
| Config | Declarative, secret-free | Git (it belongs in a repo) | Restore = checkout |

**Continuity rule:** the hash chain is the evidence artifact — a restore that produces a chain mismatch is
surfaced as `tamper`/gap and requires explicit operator acknowledgment, because silent re-anchoring is
exactly the corruption an auditor (or attacker) would want.

## 5. Monitoring and health

- **`agentkeys doctor`** — effective config, backend health/latency, capability flags, clock skew, last
  denial reason; non-zero exit on anything that would deny issuance.
- **`agentkeys verify-log`** — chain integrity; **any** mismatch is a security event, not data hygiene
  (I8).
- **`agentkeys posture`** (R18, v0.1.x) — residual risk: env-resident secrets, unbrokered servers, TTL
  drift, revocations per agent.
- **Events** — the lifecycle set ([PRD 15 §4](15-data-model.md)) is the monitoring feed; `evasion-detected`,
  `exchange-rejected`, and `revoked` are the three that page a human. Telemetry to the sink is opt-in and
  secret-free (E5).

## 6. Incident-response runbooks

Each follows **symptom → immediate action → verification → follow-up**. The runbook files live in
`docs/runbooks/`; this section is the index and the semantics.

| # | Runbook | Symptom | Immediate action | Verification |
|---|---|---|---|---|
| **rb-1** | Backend locked / unavailable | Issuances denied; `doctor` names the backend | Unlock/restore the backend; **never** bridge with a literal secret (E4) | `doctor` green; a test issuance succeeds; denials logged with reasons |
| **rb-2** | Store corruption / chain mismatch | `verify-log` non-zero; broker stops issuing | Stop; backup the store as-is; restore last good; **acknowledge the gap explicitly** | `verify-log` green before serving; gap/tamper events retained |
| **rb-3** | Suspected exfiltration | `evasion-detected` spikes; context-dump suspicion | **`agentkeys revoke --agent <id>` (or `--all`)**; then agenthalt compose if needed | Replay of the pre-revoke credential **fails** (≤1s measured); `revoked` event attributed; then forensics from the export |
| **rb-4** | Config drift / tamper | Integrity check failure at session start; `doctor` diff | Diff vs the config repo; restore reviewed config; treat as a **security event** | Integrity check passes; tamper event reviewed, not dismissed |
| **rb-5** | Upgrade day | New binary, old store/recipes | Follow §3; pin recipes to tested versions | `doctor` + `verify-log` + one recipe smoke per Tier-1 harness |
| **rb-6** | Sink outage | agentwatch unreachable; local ledger carries gap markers | Nothing user-facing breaks — the local ledger is authoritative; repair the sink | Gap markers accounted for on repair; no issuance was lost or silently allowed |
| **rb-7** | Revoke drill (quarterly) | None — scheduled | Run the kill-time pack end-to-end on production-like state | p95 **and** max ≤1s; scoped kills don't over-kill; **drill result entered by hand** in the report |
| **rb-8** | Backend secret rotated | Upstream rotation in the vault/keychain | Nothing — references re-resolve; agents never restart (CUJ-10) | Post-rotation call succeeds; pre-rotation token dead within TTL |

**The one rule under all eight:** no runbook step may ever place a literal secret into a config, an env, or
a chat. If the fix requires that, the fix is wrong (D-06, [PRD 14 §4](14-non-goals.md)).

## 7. Governance (who may change what)

| Change | Owner | Review | Record |
|---|---|---|---|
| Broker config (bindings, TTLs, enforce mode) | The machine's owner (Maya) | Config-as-code review — a PR, not a vibe | Ledger `config` events + integrity digest |
| Policy (what requires step-up, class assignments) | agentpolicy | agentpolicy's governance (Cedar, versioned) | The decision record cited in `provenance` |
| Backends (add/remove) | Owner + conformance suite | A backend that cannot pass conformance is **rejected at load** | Backend registry events |
| Recipes | Repo maintainers | The pack gates it | Compatibility table in release notes |
| Revocation | **Any operator, unconditionally** | Never gated (D-07) — governance is the *event*, not a gate | `revoked` with principal + effective_at |

## 8. Retention, export, and evidence

- **Retention is local and explicit:** the ledger is append-only; pruning is a logged operation (a new
  event naming what was pruned and why) — never a silent delete. Default windows are **not yet frozen**
  ([PRD 15 §8](15-data-model.md)).
- **Export is the evidence interface:** `agentkeys export --session/--reference` emits deterministic,
  secret-free JSONL (scanned — SC-43) that auditors and agentcomply consume directly.
- **The field-test report is hand-maintained** — operational verdicts (drill results, incident notes) are
  entered by hand from committed results; automation never writes it (repo `AGENTS.md`, [PRD 21
  §5](21-evidence-register-and-method.md)).

## 9. Server-mode ops preview (R11 — not yet)

When the fleet broker lands, this document grows: rolling upgrades with epoch-correct revokes, central
config distribution (still declarative, still integrity-checked), per-team policy namespaces (still owned
by agentpolicy), and fleet revoke drills. **None of it weakens a v0.1.0 guarantee:** local semantics are
the floor every mode inherits.

## 10. Related documents

- Failure semantics behind every runbook: [PRD 02 §6](02-architecture.md).
- The invariants no operation may breach: [PRD 06](06-security-baseline.md).
- Evidence labels for every operational claim: [PRD 20 §6](20-standards-and-claims.md), [PRD 21](21-evidence-register-and-method.md).
- Enterprise deployment path: [PRD 23](23-enterprise-adoption-and-hardening.md).
