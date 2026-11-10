# Ops reference — serve, backup/restore, retention, drills

> **Status: implemented (M12).** Design: [ops design](../design/v0.1.0/ops.md).

## `agentkeys serve`

Runs the broker in the foreground: opens the store (single writer), writes `$AGENTKEYS_HOME/serve.lock`
(`0600`), and exits `0` on SIGTERM/SIGINT after closing the store and removing the lock. A lock whose PID
is gone is **stale**; `doctor` reports it and a second `serve` refuses until it is cleared. `--write-units`
writes the launchd `LaunchAgents` plist and the systemd **user** unit into `$AGENTKEYS_HOME/units` (never
root) and exits.

## `agentkeys backup --out FILE`

WAL-safe SQLite online copy, verified chain, plus `FILE.manifest.json` (`0600`) with `schema_version`,
`rows`, `chain_head`, `created_at`. The store holds references, bindings, issuance **hashes**, the ledger,
and receipts — never a secret value.

## `agentkeys restore --from FILE`

Refuses a live broker, a backup with a broken chain (`TAMPER`, bad `seq` named), or a backup newer than this
binary's schema. Restores atomically and preserves the chain exactly; it never re-anchors and never
resurrects a revoked decision.

## Migrations

Forward migrations run on open; a store with a newer `schema_version` refuses loudly (`StoreVersionError`)
and writes nothing. Downgrades are not supported.

## Retention

`RetentionPolicy.prune(before_seq)` appends one `retention-pruned` event naming the cutoff. Ledger rows are
**not** deleted in v0.1.0 (deletion would break the chain); physical pruning is an honest future operation.

## Revoke drill

`python -m agentkeys.bench.killtime --iterations 100` emits JSON (`p50_ms`, `p95_ms`, `max_ms`,
`replay_failures`, `passed`). The drill verdict is entered by hand in the field-test report.

## Doctor checks

`platform`, `config`, `home`, `store`, `chain`, `backends`, `clock`, `serve-lock`, `config-integrity`,
`version`. Exit precedence is `tamper (3) > denied (2) > ok (0)`.
