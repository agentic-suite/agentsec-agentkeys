# Quickstart — first brokered credential in 15 minutes

> **Status: implemented (M13).** Every command on this page is replayed by
> `tests/docs/test_quickstart.py` (`scan → migrate → ref → run → revoke → replay → export → verify-log`).
> Commands not on this page are either not yet available or are marked in
> [honest gaps](../explanation/honest-gaps.md).

**BLUF:** write a references-only config → scan a repo → migrate one secret to the file backend → make a
brokered child-process call where the child receives a scoped token at its own egress → revoke → prove the
replay fails → export and verify the hash-chained lifecycle.

## Minutes 0–3 — config

```sh
mkdir -p ~/.agentkeys && chmod 700 ~/.agentkeys
cat > ~/.agentkeys/config.toml <<'TOML'
enforce_mode = "enforce"
sink = ""

[store]
path = "~/.agentkeys/agentkeys.db"

[clock]
skew_tolerance = 30

[ttl.dev]
floor = 30
ceiling = 900

[[backends]]
id = "file"
precedence = 1

[[bindings]]
reference = "akref:file/agentkeys/dev/github_token"
audience = "api.example.com"
tool = "call"
TOML
```

`agentkeys doctor` explains the effective config, the store schema, the ledger chain, and the serve lock.

## Minutes 3–6 — find and migrate one secret

```sh
agentkeys scan --root .
agentkeys migrate .env GITHUB_TOKEN --root .
agentkeys ref list
```

`scan` prints masked findings only — path, line, class, field, length — **never the value**. `migrate`
moves the value into `~/.agentkeys/credentials.json` (`0600`), registers the reference, and rewrites every
use site to `akref:file/agentkeys/dev/github_token`. Re-run `scan`: the finding is closed.

## Minutes 6–9 — the brokered call

```sh
AGENTKEYS_SCOPED_TOKEN=akref:file/agentkeys/dev/github_token \
agentkeys run --server akref:file/agentkeys/dev/github_token -- python -c \
  "import os,sys; sys.exit(0 if os.environ.get('AGENTKEYS_SCOPED_TOKEN') else 3)"
```

The child's environment names the **reference** (`NAME=akref:…`); the broker substitutes the scoped token
at spawn time, so the child authenticates and the transcript holds only the reference.

The child is launched under the broker. Its environment holds the **scoped token** (delivered at egress),
never the reference config's value; the agent transcript holds only the reference (R2, R8).

## Minutes 9–11 — proof: the one-second kill

```sh
agentkeys revoke --session stdio
agentkeys replay --last
# exit 4: REFUSED (exchange-rejected): session-revoked
```

Revoke is a CAS on the session epoch. `replay --last` exits `4` **only** when the pre-revoke resolution is
refused; a still-working replay exits `2` — a fast command with a live token is not evidence (R4, SC-24).

## Minutes 11–15 — the evidence

```sh
agentkeys export --session stdio --out lifecycle.jsonl
agentkeys verify-log
```

The export is deterministic, `0600`, and secret-free; `verify-log` recomputes the hash chain and exits `3`
on any tamper (R6, E12).

## What just happened

| Step | The property you exercised |
|---|---|
| scan / migrate | the credential left the agent's readable world — R17 |
| ref | the agent holds references, never values — R1 |
| run | resolution at moment-of-use, injection at egress — R2/R8 |
| revoke + replay | unconditional kill, replay-verified — R4 |
| export + verify | attributed, hash-chained lifecycle — R6/E12 |

## Honest gaps in this flow

- `migrate --backend keychain` is **not yet** available; the file backend (`0600`) is used.
- `agentkeys init`, `context-dump`, and `scan-usable` are **not yet** implemented.
- The harness recipes are documented and smoked in tests; a live Claude Code / Cursor call is a
  field-test step (M14), not claimed here.
