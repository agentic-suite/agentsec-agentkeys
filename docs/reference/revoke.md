# Revocation reference — `agentkeys revoke` / `agentkeys replay`

> **Status: implemented (M6).** Design: [revoke design](../design/v0.1.0/revoke.md).

## `agentkeys revoke`

| Flag | Meaning |
|---|---|
| `<session-id>` (positional) | revoke one session; `all` revokes everything |
| `--session ID` | revoke one session |
| `--agent ID` | revoke every session of one agent |
| `--all` | revoke every session in the store (explicit) |
| `--reason TEXT` | recorded on the `revoked` event (default `operator`) |
| `--principal NAME` | operator identity recorded on the event (default `operator`) |
| `--json` | stable envelope |
| `--config PATH` | config path (default `$AGENTKEYS_HOME/config.toml`) |

Revocation is a compare-and-set on `sessions.revoke_epoch`. It is **unconditional** (never policy-gated)
and **scoped**: a session kill leaves other sessions authenticating; `--all` is the only explicit
everything-kill. An unknown session/agent exits `2` (`denied`) naming the target — never a silent no-op.

Exit codes: `0` revoked · `2` unknown target / config or store failure · `1` usage (no target, ambiguous
flags).

## `agentkeys replay --last`

Re-runs the resolution of the last pre-revoke issuance. Exit `4` (`revoke_verified`) means the replay was
**refused** (`REFUSED (exchange-rejected): session-revoked`) — the only accepted kill-time proof. If the
replay still resolves, the command exits `2` with `revocation-not-effective`.

## Kill-time harness

`python -m agentkeys.bench.killtime --iterations 100` emits JSON with `p50_ms`, `p95_ms`, `max_ms`,
`replay_failures`, and `passed`. PASS requires `p95_ms <= 1000` **and** `max_ms <= 1000`
([SC-24](../prd/17-scenarios.md)); the exit code is `0` on pass and `1` on fail.
