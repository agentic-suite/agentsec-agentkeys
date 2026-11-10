# Foundation design — agentkeys v0.1.0 (M0)

**Status:** design of record for M0 · **Issue:** #5 (`0.D0`) · **Review:** self-review recorded below ·
**Written before any implementation code.**

**BLUF:** M0 builds an installable, CI-gated, stdlib-only Python project named `agentsec-agentkeys` that
ships one binary, `agentkeys`. It freezes three contracts that every later milestone consumes: the **command
surface**, the **reserved exit codes**, and the **references-only configuration model** rooted at
`AGENTKEYS_HOME`. Nothing brokers a credential in M0 — every broker command is an honest stub that exits
non-zero with a reason. `doctor` is the only command with real checks.

This document is the source of truth for M0. Implementation items (`0.1`–`0.7`) must match it; a divergence
is a bug in the code, not an amendment to the design.

---

## 1. Identity & packaging

| Item | Decision |
|---|---|
| Distribution name | `agentsec-agentkeys` (`pip install agentsec-agentkeys` — published v0.1.0) |
| Import package | `agentkeys` (`src/` layout) |
| Console script | `agentkeys` |
| Runtime dependencies | **none** — Python **stdlib only** (PRD 13 §5) |
| Python floor | **3.11+** (`tomllib`, `StrEnum`) |
| Platforms | macOS + Linux. **Windows is explicitly unsupported** and must say so, not fail cryptically. |
| Layout | `src/agentkeys/` · `tests/` · `docs/` · `Makefile` · `pyproject.toml` |

Dev-only dependencies (never runtime): `pytest`, `pytest-cov`, `ruff`, `mypy`. `make setup` creates the
virtual environment / installs the editable package plus dev extras; `make lint`, `make typecheck`,
`make test`, `make cov`, `make gate` are the quality surface. `make gate` = lint + typecheck + cov ≥ 95%.

Version is defined **once** in `src/agentkeys/__init__.py` as `__version__`, and `pyproject.toml` reads it
dynamically (`[tool.setuptools.dynamic]`). No duplicated version string.

## 2. Command surface (frozen in M0)

`agentkeys --help` lists exactly these commands. Any command not listed here does not exist in v0.1.0.

| Command | M0 behavior |
|---|---|
| `init` | stub — refuses (exit `1`) until the config writer lands |
| `doctor` | **implemented** — read-only health checks, exit-coded |
| `scan` | stub |
| `migrate` | stub |
| `ref` | stub (reserved subcommands: `list`, `show`) |
| `run` | stub |
| `revoke` | stub |
| `replay` | stub |
| `context-dump` | stub |
| `scan-usable` | stub |
| `export` | stub |
| `verify-log` | stub |
| `conformance` | stub |
| `serve` | stub |
| `version` | **implemented** — prints `agentkeys <version>`, exit `0` |

Rules for every stub:

1. It parses its documented flags (`--json`, `--help`, plus the flags in
   [CLI reference](../../reference/cli.md)) so the surface is visible in `--help`.
2. Invoked for real, it prints a **clear, non-empty** message to stderr naming the milestone that will
   deliver it (e.g. `agentkeys scan: not implemented in v0.1.0 M0 (planned: M8)`) and exits `1`.
3. A stub never pretends to succeed, never prints a secret, and never writes state.
4. `--json` is accepted everywhere and yields the stable envelope
   `{"ok": bool, "exit_class": str, "reason": str?, "data": any, "receipts": []}`. In M0 the stub envelope
   has `ok: false`, `exit_class: "usage"`.

Unknown subcommands and unknown flags exit `1` (usage), never `0`.

## 3. Reserved exit codes (frozen contract)

Single owning module: `agentkeys/exit_codes.py`. Every command that maps a decision MUST use it — no
integer literals at call sites.

| Code | Name | Meaning | CI |
|---|---|---|---|
| `0` | `OK` | success; for `scan-usable`, **0 usable credentials** (invariant holds) | pass |
| `1` | `USAGE` | usage / internal error (unknown command, bad flag, unimplemented stub) | fail |
| `2` | `DENIED` | fail-closed denial with a reason (backend locked/absent/ambiguous, binding mismatch, no approval) | fail |
| `3` | `TAMPER` | integrity failure (chain break, corrupt store, config integrity check) | fail (security event) |
| `4` | `REVOKE_VERIFIED` | replay refused after revoke — the kill-time proof | pass |

The enum is **additive-only within v0.x**: a future code is added, never an existing code renumbered or
repurposed (E11). Values `0`–`4` are asserted by fixture once and treated as a compatibility contract.

`doctor` exits `0` when healthy, `2` when any check fails (unhealthy = would deny issuance), `3` when a
tamper-class condition is detected, `1` on usage errors.

## 4. Configuration model

TOML, loaded and validated at every command start. **Fail closed:** a missing, malformed, ambiguous, or
secret-bearing config refuses to run with an actionable error (exit `1` for usage/invalid config; `doctor`
reports it and exits `2`). Never defaults to a permissive value.

Location: `$AGENTKEYS_HOME/config.toml`; `AGENTKEYS_HOME` defaults to `~/.agentkeys`. An explicit
`--config <path>` (where exposed by a command) overrides the location but **not** the validation rules.

### Keys (PRD 15 §7)

```toml
enforce_mode = "enforce"          # monitor | enforce   (required)
sink = ""                         # agentwatch endpoint; "" = local ledger only (required)

[store]
path = "~/.agentkeys/agentkeys.db"  # required

[clock]
skew_tolerance = 30               # seconds; integer >= 0 (required)

[ttl.dev]
floor = 30                        # seconds; integer > 0
ceiling = 900                     # seconds; must be >= floor
[ttl.prod]
floor = 30
ceiling = 300

[[backends]]
id = "keychain"                   # unique, non-empty
precedence = 1                    # integer >= 1; unique per config
[[backends]]
id = "file"
precedence = 2

[[bindings]]
reference = "akref/1.0"           # reference document path/URI — never a secret
audience = "api.github.com"
tool = "gh"
```

Validation rules (each violation fails closed with the failing key named):

- **Unknown top-level or nested key** → error (`unknown key: <dotted.path>`); no silently ignored keys.
- Required keys absent → error naming the key.
- `enforce_mode` must be `monitor` or `enforce`.
- `ttl.<class>`: at least one class; `floor > 0`; `ceiling >= floor`; class in
  `public|dev|staging|prod`; duplicate class rejected by TOML.
- `backends`: at least one; `id` unique and non-empty; `precedence` unique; **no duplicate precedence**
  (ambiguity is a refusal, never first-match-wins).
- `bindings`: `reference`, `audience`, `tool` all non-empty strings; duplicates rejected.
- `store.path` non-empty; parent directory need not exist yet (created by `init` later), but a path pointing
  at an existing directory is an error.
- `clock.skew_tolerance` integer `>= 0`.
- **References only:** any string value matching a known credential shape (`sk-…`, `ghp_…`, `github_pat_…`,
  `AKIA…`, `xox[baprs]-…`, PEM `-----BEGIN … PRIVATE KEY-----`, or a JWT `eyJ…`.`…`.`…`) is a
  **literal-secret error** naming the dotted key. The value is never echoed into the error message; only the
  redaction-safe location is printed.
- `bindings[].reference` must look like an `akref/1.0` reference (path or `akref://` URI). A backend-native
  secret path in a key position is not accepted as a reference.

Config discovery order (first hit wins, no merging — merging is ambiguity):

1. `--config <path>` argument, if the command accepts one;
2. `$AGENTKEYS_HOME/config.toml`;
3. `~/.agentkeys/config.toml` when `AGENTKEYS_HOME` is unset.

No config file at all is a **missing config** error for commands that need it (`doctor` reports it as a
failed check). The `~` expansion applies to `store.path` and `AGENTKEYS_HOME` only.

### `AGENTKEYS_HOME` layout (sketch)

```text
$AGENTKEYS_HOME/                 # default ~/.agentkeys, dir 0700
├── config.toml                  # 0600 — references only, never a secret
├── agentkeys.db                 # 0600 — SQLite WAL store (M1); absent in M0
├── agentkeys.db-wal / -shm      # created by SQLite when the store opens (M1)
└── logs/                        # optional local diagnostics (never secrets)
```

Permissions are part of the contract: the home directory is `0700`, the store and config are `0600`.
In M0 only `doctor` checks them; `init` (a later milestone) creates them.

## 5. Store layout sketch (consumed by M1)

M0 does **not** open or create a store. It records the shape the M1 BrokerStore driver will use so config
keys (`store.path`) and `doctor` (schema version check) are stable:

- single-file SQLite, WAL mode, `synchronous=FULL`, single writer;
- a `schema_version` table (integer, forward migrations only; downgrade refuses loudly);
- tables sketch: `references`, `sessions`, `bindings`, `issuances`, `revocations`, `ledger`
  (append-only, hash-chained), `backend_registry`, `redaction_receipts`;
- no column ever holds secret material — only `secret_hash` and class labels (PRD 15 §6).

`doctor` reports the schema version as `absent` (healthy for a fresh install, no store yet) or the version
read from `schema_version`.

## 6. `doctor` checks (M0)

Read-only; never writes. Ordered, each with an id, and each rendered by `--json`:

| Check | Healthy when | Failure exit |
|---|---|---|
| `platform` | `sys.platform` is `darwin`/`linux` (Windows → actionable "not supported") | `2` |
| `config` | config exists, parses, validates (references only) | `2` (missing/invalid) / `3` (literal secret) |
| `home` | `AGENTKEYS_HOME` exists and is a directory, mode `0700` | `2` |
| `store` | `store.path` parent exists and is writable; store absent → `schema_version: absent`; store present → readable + version known | `2` (unreadable) / `3` (corrupt/unknown version) |
| `backends` | at least one backend, unique ids/precedence (registry validation) | `2` |
| `clock` | wall clock readable; `skew_tolerance >= 0`; no backwards jump within the process | `2` |
| `version` | `agentkeys --version` matches the package version | `2` |

Human output: one line per check (`ok` / `fail` / `skip`) plus the effective config summary (paths,
enforce mode, backend order, TTL bounds). `--json` emits the envelope with `data.checks[]` and
`data.effective_config`. Exit precedence: `3` (tamper) > `2` (denied) > `0` (ok).

## 7. Security invariants honored by M0

- **I1 never-in-context:** no command prints a secret; stubs print no state at all; config errors name keys,
  never values.
- **I2 fail closed:** missing/ambiguous config denies; unknown keys deny; Windows denies with a clear reason.
- **I6 outside the control plane:** config lives under `AGENTKEYS_HOME`, not in the agent's project tree by
  default.
- **I7 redaction before persistence:** M0 persists nothing; the config validator refuses secret-shaped
  values instead of storing them.
- **I10 supply chain:** CI runs lint/type/test/coverage; DCO enforced; no runtime third-party code.

## 8. Out of scope in M0 (honest limits)

- No credential is brokered, issued, stored, or revoked; every broker command is a stub.
- No store file is created or opened; `store.path` is validated only.
- No backend is contacted; `backends` is a registry of ids, not a live driver set.
- No `init` config writer (planned with M1/M3), no `--json` success data beyond `doctor`/`version`.
- Windows is unsupported; the CLI says so.

## 9. Review

Self-review against PRD 02 §6 failure semantics, PRD 13 §5/§7/§10, PRD 15 §7, PRD 14 scope guard, and the
M0 WBS table. Findings resolved in this document: (1) `version` is implemented rather than stubbed, to
avoid a nonsensical refusal; (2) confirmation that ambiguity is refusal — never merge config sources or
first-match backends; (3) exit precedence for `doctor` fixed as `3 > 2 > 0`; (4) config errors do not echo
offending values, only dotted key names. Open questions deferred to their owning milestones: retention
windows (M7), backend conformance gating (M3), store schema detail (M1).

Code review of the implementation is tracked in
[`docs/wbs/v0.1.0/codereview-log.md`](../../wbs/v0.1.0/codereview-log.md).