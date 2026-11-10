# Operations design — serve, backup/restore, retention, drills (M12)

**Status:** design of record for M12 · **Issue:** #148 (`12.D0`) · **Written before implementation.**
**Sources:** [PRD 22 §2–§6](../../prd/22-operations-and-governance.md), [PRD 13](../../prd/13-non-functional-requirements.md),
[PRD 05 R4/E4/E12](../../prd/05-features.md), [store design](store.md), [revoke design](revoke.md).

**BLUF:** the broker must survive its worst operational day. `serve` runs a user-scoped broker with a lock
file that makes a dead instance obvious; backup is a WAL-safe copy that carries **references only** and a
chain head; restore refuses a tampered backup and never resurrects a decision; retention is a logged marker,
never a silent delete; the revoke drill emits machine-readable kill-time numbers. Downgrades refuse loudly.

---

## 1. `serve` + service units

- `agentkeys serve` opens the configured store (single writer), writes `$AGENTKEYS_HOME/serve.lock`
  (`{pid, started_at, store, version}`) `0600`, and waits. SIGTERM/SIGINT flush and close the store, then
  remove the lock (exit `0`).
- A `serve.lock` whose PID is not alive is **stale**: `doctor` reports it and a second `serve` refuses until
  it is cleared — a dead lock never silently allows a second writer.
- Units are user-scoped: launchd `LaunchAgents` (no `root`) and a systemd **user** unit
  (`systemctl --user`). Both only run `agentkeys serve` with the user's `AGENTKEYS_HOME`.

## 2. Backup / restore

`agentkeys backup --out FILE` uses SQLite's online backup API (WAL-safe) and then verifies the copy's chain.
The manifest (`FILE.manifest.json`, `0600`) records `schema_version`, `rows`, `chain_head`, `created_at`.
The database never contains a secret value, so "references only" is structural.

`agentkeys restore --from FILE` refuses when a live `serve.lock` exists, refuses a backup whose chain is
broken (`TAMPER`, naming the bad `seq`), refuses a backup newer than this binary's schema, and otherwise
replaces the store atomically (`0600`). Restore never re-anchors a chain and never resurrects a decision:
revocations and ledger rows are restored exactly as backed up.

## 3. Migrations + downgrade

`SqliteStore.open()` migrates forward; a store with a newer `schema_version` raises `StoreVersionError` and
writes nothing. A released schema is never renumbered (E11).

## 4. Retention

`RetentionPolicy.prune(before_seq, actor=…)` appends one `retention-pruned` event naming the cutoff and
returns it. Rows are **not** deleted in v0.1.0 (deleting would break the chain); physical pruning is an
honest future operation. The export path stays secret-free (evidence scanner).

## 5. Revoke drill

`run_drill(store, core, …)` wraps the M6 kill-time benchmark and returns the report plus `generated_at`;
`python -m agentkeys.bench.killtime` is the CLI form. The verdict is entered **by hand** into the field-test
report — automation never writes it.

## 6. `doctor` hardening

New checks: `chain` (tamper on a broken chain), `serve-lock` (stale lock is a denial), `config-integrity`
(a pinned `config.sha256` mismatch is tamper), in addition to config/store/backends/clock/home. Exit
precedence stays `tamper (3) > denied (2) > ok (0)`; the whole run is target < 2s.

## 7. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 12.1 | `tests/test_serve_units.py` | lock lifecycle, stale lock, SIGTERM cleanup, units have no root |
| 12.2 | `tests/test_backup_restore.py` | WAL-safe copy, manifest, tamper refused, no live-lock restore |
| 12.3 | `tests/test_schema_migration.py` | forward migrate; downgrade refuses loudly |
| 12.4 | `tests/test_doctor_ops.py` | chain/lock/config-integrity checks and exit precedence |
| 12.5 | `tests/test_drill.py` | drill reports p50/p95/max and pass/fail |
| 12.6 | `tests/test_retention.py` | prune appends a marker, deletes nothing, chain stays intact |

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `12.CR`.
