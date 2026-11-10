# Recipe: Cursor (Tier-1)

> **Status: implemented (M10; SC-36).** Smoke: `tests/test_harness_recipe_cursor.py`.

Cursor reads MCP servers from `.cursor/mcp.json` (project) or the user-level equivalent. Use the **same**
broker wrapper as Claude Code; the only difference is the egress direction — an HTTP target is
authenticated with a broker-injected header.

## `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "agentkeys": {
      "command": "agentkeys",
      "args": ["run", "--server", "akref:keychain/agentkeys/dev/token", "--", "npx", "-y", "@example/mcp-server"],
      "env": {}
    }
  }
}
```

For a direct HTTP target, bind the reference to the header egress (`HeaderInjector`): `Authorization:
Bearer <broker-token>`. Any client-supplied credential header is removed before the broker sets its own
(no passthrough, E14).

Rules are identical to the Claude Code recipe: `command` is `agentkeys`, `--server` is a reference, `env`
is reference-only. The wiring is validated by `agentkeys.recipes.validate_wiring`; a missing or drifted
wiring fails loudly rather than bypassing the broker.
