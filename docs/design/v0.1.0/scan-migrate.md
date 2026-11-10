# Scan & migrate design — find what the agent can read, move it out (M8)

**Status:** design of record for M8 · **Issue:** #101 (`8.D0`) · **Written before implementation.**
**Sources:** [PRD 05 R17](../../prd/05-features.md), [PRD 17 SC-51](../../prd/17-scenarios.md),
[PRD 04 CUJ-1](../../prd/04-users-and-cujs.md), [backend design](backends.md), [PRD 15 §8](../../prd/15-data-model.md).

**BLUF:** `agentkeys scan` reports **where** a candidate secret sits and **what shape** it is, never the
value. `agentkeys migrate` moves one value into a backend and rewrites every use site to a reference,
in one guided step. Safety is structural: the scanner has no rendering path for a value, and a failed
migration leaves every source file byte-identical.

---

## 1. Scan classes

Detection reuses the **single source of credential-shape knowledge** — `agentkeys.redact.SECRET_CLASSES`
(api-key, bearer, jwt, private-key, connection-string, env-assignment) — plus the file kinds an agent
can read:

| File kind | Why it matters |
|---|---|
| `.env`, `*.env` | the classic env-resident secret |
| `mcp.json`, `*.mcp.json`, `.mcp.json` | stdio server `env` blocks (row #8) |
| `*.json`, `*.toml`, `*.yaml`, `*.yml` | harness settings / config-embedded values |
| `*.sh`, `*.bash`, `*.zsh` | exported secrets in shell scripts |
| `*.pem`, `*.key` | private-key blocks |

Every match is a `Finding{path, line, field, class, length}` — **no value, no tail, no preview**.
`field` is the assignment/JSON key when one is present.

**Broad reuse** — the same value (compared by SHA-256 digest, never by plaintext comparison in
output) appearing at two or more sites is flagged `broad_reuse=True` with the site list. The blast
radius smell is the finding, not the secret.

## 2. Migrate flow

```python
plan = Migrator(store, writer).plan(root, path, name)     # value + every re-use site (masked)
result = Migrator(store, writer).migrate(root, path, name)  # backend write -> register -> rewrite
```

1. **Read + plan** — locate the value for `name`; find every site with the same digest; compute the
   new file text with the plaintext replaced by `akref:<backend>/<slot>`. Nothing is written yet.
2. **Write the backend** — `SecretWriter.write(slot, value)`. A backend failure aborts here with
   every source file untouched.
3. **Register the reference** — `ReferenceRegistry.register(...)` through the store contract. A
   registration failure deletes the just-written backend value and aborts.
4. **Rewrite the sites** — atomic `os.replace` per file after all temp files are written; on a write
   failure the already-replaced files are restored from the in-memory originals.

Writers: `FileSecretWriter` (a `0600` JSON credential file, the R5 fallback backend). The keychain
writer is not implemented in v0.1.0 and refuses honestly — no silent downgrade is possible because the
caller names the backend.

## 3. Surfaces

```
agentkeys scan [--root DIR] [--json]              # masked findings; --ci refuses honestly (v0.1.x)
agentkeys migrate FILE NAME [--backend file] [--root DIR] [--dry-run] [--json]
```

Exit codes: `OK` for a completed scan (findings or not) and a completed migration; `DENIED` for an
unknown name, an unavailable backend, or a failed rewrite; `USAGE` for an unsupported option
(`--ci`, unknown backend).

## 4. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 8.1/8.4 | `tests/test_scan_candidates.py` | 100% recall on the fixture corpus; broad reuse flagged |
| 8.2 | `tests/test_scan_candidates.py` | zero planted values in any output (human + JSON) |
| 8.3 | `tests/test_migrate_flow.py` | value moves to backend; every site rewritten; re-scan clean; failure leaves files untouched |
| 8.5 | `tests/test_scan_cli.py` | `--json` stable; `--ci` refuses as "not yet" |

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `8.CR`.
