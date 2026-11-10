# stdio MCP credential virtualization (v0.1.0)

**Status:** implemented in M5 · **Owner modules:** `src/agentkeys/stdio/` ·
**Design:** [stdio design](../design/v0.1.0/stdio.md) · **Issue:** WBS 5.D.

**BLUF:** `agentkeys run --server <ref> -- <server argv>` launches a stdio MCP server (or CLI) with an
environment that holds **references and placeholders, never secrets**. The broker resolves each placeholder
to a short-lived, scoped token at spawn time and proxies the JSON-RPC stream untouched.

## The reference/placeholder pattern (for server authors)

A server's configuration names a **slot**, not a value:

```jsonc
// mcp.json — safe to commit, log, and dump into an agent's context
{
  "mcpServers": {
    "issues": {
      "command": "agentkeys",
      "args": ["run", "--server", "akref:keychain/agentkeys/dev/issues-token", "--", "issues-mcp"],
      "env": { "ISSUES_TOKEN": "akref:keychain/agentkeys/dev/issues-token", "LOG_LEVEL": "info" }
    }
  }
}
```

At spawn the broker replaces `ISSUES_TOKEN` with a scoped token (`audience` from the binding, `tool` from the
binding, `session` = the run's session). The server's own code is unchanged: it reads `ISSUES_TOKEN` as
before — it is simply never asked to hold a durable secret.

**Rules the wrapper enforces**

| Rule | Effect |
|---|---|
| references in, tokens out | every `akref:<backend>/<path>` placeholder is substituted; a malformed one is refused |
| no passthrough (E14) | a *literal* value in a credential variable (`GITHUB_TOKEN`, `OPENAI_API_KEY`, …) is stripped before the child starts |
| transparent proxy | frames pass byte-for-byte; oversized frames are refused, never truncated |
| stderr-only logging | the JSON-RPC stream on stdout is never written to by the broker |
| scoped substitution | each placeholder resolves through `ResolutionCore`, so the token is bound to one audience/tool/session and is single-use |

## The honest co-located-runtime limit

This is a **process-boundary** mechanism, and it is worth being precise about what that buys:

- The child receives a **scoped, short-lived, single-use token at use time**, not the underlying long-lived
  credential. A scan of its config, environment, logs, and the agent's transcript finds zero credentials.
- If the child shares a runtime where arbitrary agent code can read the broker's memory or the token it was
  handed, that runtime can read **that token** — scoped to one audience/tool/session, expiring, and killable
  with `agentkeys revoke` (≤1s).
- Where that boundary cannot be established, agentkeys **says so** and records the attempt; it never claims a
  guarantee it cannot hold. (PRD 06 §4; recorded in the M14 field-test report.)

## Limits at v0.1.0

- The wrapper is exercised end-to-end against a stock JSON-RPC child in the test suite; live harness recipes
  (Claude Code, Cursor) land in M10, and the M14 field test runs them on a real box.
- Frame handling is line-delimited JSON-RPC; a server that speaks a different framing is out of scope.
- `agentkeys run` creates its own local session (`--session` to name it); a harness integration with a
  pre-existing session arrives with the M10 recipes.
