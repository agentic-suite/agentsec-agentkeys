# CLI reference — the designed v0.1.0 surface

> **Status: design of record.** This is the planned command surface — the target that
> `tests/docs/test_cli_coverage.py` enforces when v0.1.0 ships: a flag may not exist in the CLI without
> being documented here, and a flag may not be documented here without existing in the CLI. The contracts
# and exit codes below are **stable within v0.x** (additive only, E11).

`--version` prints the version (a top-level flag); every command accepts `--json` where documented.

**BLUF:** One binary, `agentkeys`, fourteen commands at v0.1.0 (+1 at v0.1.x), four exit-code classes
that scripts and CI can rely on forever — and a hard rule: **no command ever prints a secret value.**

## Implementation status (M10, 2026-11-09)

`doctor`, `version`, `ref`, `run`, `revoke`, `replay`, `export`, `verify-log`, `scan`, and `migrate`
are functional. `init`, `context-dump`, `scan-usable`, `conformance`, and `serve` remain honest stubs
that exit `1` and name the milestone that delivers them.

| Command | Status | Delivered in |
|---|---|---|
| `doctor`, `version`, `ref`, `run` | implemented | M0–M4 |
| `revoke`, `replay` | implemented | M6 |
| `export`, `verify-log` | implemented | M7 |
| `scan`, `migrate` | implemented | M8 |
| `init`, `context-dump`, `scan-usable` | stub | M1/M2 |
| `conformance`, `serve` | stub | M11/M4 |

## Commands

| Command | Purpose | Key flags | Requirement |
|---|---|---|---|
| `agentkeys init` | Write the minimal config; refuse ambiguity | `--backend`, `--home` | R5, E4 |
| `agentkeys doctor` | Explain effective config/backends/clock; read-only | `--json` | E4, F8 |
| `agentkeys scan` | Find candidate secrets where agents read them (masked previews **only**) | `--root`, `--json`, `--ci` (v0.1.x) | R17 |
| `agentkeys migrate <file> <name>` | Move one secret to a backend; rewrite use sites to references | `--backend`, `--root`, `--reference`, `--config`, `--dry-run` | R17 |
| `agentkeys ref list` / `ref show <id>` | Inspect references (never values) | `--json` | R1, E1 |
| `agentkeys run -- <command>` | Launch a child (stdio server/CLI) under the broker with a virtualized env | `--server` | R2, R8 |
| `agentkeys revoke <target>` | Kill access: `--agent`/`--session`/`--all` | `--reason`, `--principal`, `--config` | R4 |
| `agentkeys replay --last` | Re-issue the last pre-revoke attempt to prove it fails (the kill-time evidence) | `--config` | R4, SC-24 |
| `agentkeys context-dump --session <id>` | Emit the agent's full world (transcript/env/args/config/logs) for scanning | `--out` | R1, SC-40 |
| `agentkeys scan-usable` | Score a context dump for **usable** credentials (0 = invariant holds) | `--json` | R1, SC-40 |
| `agentkeys export` | Deterministic, secret-free lifecycle JSONL | `--session`, `--reference`, `--out`, `--config` | R6, E12 |
| `agentkeys verify-log` | Recompute the hash chain; report gaps/tamper | `--json`, `--config` | R6, E12 |
| `agentkeys backup` | WAL-safe store backup with a verified chain head + manifest | `--out`, `--config`, `--json` | E12 |
| `agentkeys restore` | Restore a verified backup; refuses a live broker or a broken chain | `--from`, `--config`, `--json` | E12 |
| `agentkeys conformance` | Run the standards/backend suites (RFC 8693/8707/…; backend drivers) | `--suite` | E13, E9 |
| `agentkeys serve` | Run the local broker process (foreground); user-scoped units helper | `--socket`, `--config`, `--write-units`, `--json` | [PRD 22](../prd/22-operations-and-governance.md) |
| `agentkeys posture` *(v0.1.x)* | Residual-risk report: env-resident secrets, unbrokered servers, TTL drift, revoke counts | `--json` | R18 |

## Exit codes (stable contract)

| Code | Meaning | CI treats as |
|---|---|---|
| `0` | Success (and for `scan-usable`: **0 usable credentials** — the invariant holds) | pass |
| `1` | Usage / internal error | fail |
| `2` | **Denied** — fail-closed denial with a reason (backend locked, binding mismatch, no approval) | fail |
| `3` | **Tamper detected** — integrity check or chain verification failed | fail (security event) |
| `4` | **Revoke verified** — the replay was refused (used by `replay`; the kill-time proof) | pass |

`doctor` and `verify-log` are non-zero on anything that would deny issuance or indicate tamper —
cron-able, script-able, no parsing prose.

## Safety rules wired into every command

1. **No secret values, ever** — masked previews + locations only; the plaintext exists only transiently
   inside the broker at egress (E5, [PRD 15 §8](../prd/15-data-model.md)).
2. **Read-only or attributed** — anything that changes state (`migrate`, `revoke`, `ref`) emits a ledger
   event with the operator principal.
3. **Idempotent where it matters** — duplicate resolution requests return the same issuance; duplicate
   `migrate` is a no-op with a receipt (E1).
4. **Fail-closed is the exit code, not a paragraph** — denials are `2` with the reason in both human and
   `--json` form.

## Machine-readable mode

Every command accepts `--json` with a stable envelope (`{ok, exit_class, reason?, data, receipts[]}`);
the kill-time bench and the reproducibility kit consume this envelope so third-party re-runs diff cleanly
([PRD 21 §6](../prd/21-evidence-register-and-method.md)).

## Related

- Contracts behind these commands: [PRD 15 — Data model](../prd/15-data-model.md)
- The adapter recipes that use `run`: [PRD 16 — Adapters & integration](../prd/16-adapters-and-integration.md)
- Operational use of each: [PRD 22 — Operations & governance](../prd/22-operations-and-governance.md)
- Terms used above: [Glossary](glossary.md)
