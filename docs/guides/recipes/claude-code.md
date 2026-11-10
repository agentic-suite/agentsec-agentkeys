# Recipe: Claude Code (Tier-1)

> **Status: implemented (M10; SC-35).** Smoke: `tests/test_harness_recipe_claude_code.py`.

Claude Code launches stdio MCP servers from `~/.claude.json` (user scope) or `.mcp.json` (project
scope). Point the server's `command` at the broker wrapper — never at the server directly — so the child
receives a scoped token at its own egress instead of a secret from its config.

## `.mcp.json`

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

Rules:

- `command` must be `agentkeys` (no harness fork, no `npx` wrapper around the broker).
- `--server` names a **reference**, never a value.
- `env` is empty or reference-form (`akref:…` / `op://…`); `validate_wiring` refuses a literal secret.

## Verify

```bash
agentkeys scan --root .            # the config must hold no secret shape
agentkeys ref list                 # the reference is registered, no value printed
```

`run_recipe_smoke` in `agentkeys.recipes` resolves through the broker, injects into the child environment,
and asserts the target authenticates the **broker-minted** token while the transcript holds only the
reference.
