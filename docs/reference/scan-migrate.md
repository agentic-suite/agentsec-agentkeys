# Scan & migrate reference — `agentkeys scan` / `agentkeys migrate`

> **Status: implemented (M8).** Design: [scan/migrate design](../design/v0.1.0/scan-migrate.md).

## `agentkeys scan`

`--root DIR` (default `.`), `--json`, `--ci`.

Scans `.env`/`*.env`, `*.json`, `*.toml`, `*.yaml`, `*.yml`, `*.sh`/`*.bash`/`*.zsh`, `*.pem`, `*.key`
for the credential shapes in `agentkeys.redact.SECRET_CLASSES`. Output is **masked**: path, line, class,
field, length, and a `broad-reuse` flag — never a value and never a value tail.

- `--json` emits `{"root","files_scanned","findings":[…],"summary":{class:count},"broad_reuse":N}`.
- `--ci` is **not yet** available (v0.1.x) and refuses with exit `1`; no CI gate is claimed.
- Exit `0` for a completed scan (findings or not); `2` when the root is not a directory.

## `agentkeys migrate FILE NAME`

`--backend` (only `file` in v0.1.0; anything else refuses as "not yet available"), `--root DIR`
(the site-rewrite scope), `--reference ID`, `--config PATH`, `--dry-run`, `--json`.

1. Locates `NAME` in `FILE` and every site sharing the same value (SHA-256 digest).
2. Writes the value to the backend (`$AGENTKEYS_HOME/credentials.json`, `0600`).
3. Registers the reference through the store.
4. Rewrites every site to `akref:<backend>/<slot>` atomically, restoring originals on failure.

A backend failure or a failed rewrite leaves every source file untouched (SC-51). After migration a
re-scan shows the finding closed. `--dry-run` writes nothing and prints a masked plan.
