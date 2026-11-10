# Harness recipes — one broker, every harness

> **Status: implemented (M10; smokes in `tests/test_harness_recipe_*.py`).** Live harness runs are M14.

Every recipe is configuration, not a code fork: `command: agentkeys run --server akref:… -- <server>`
with reference-only `env`. The broker sits below the harness, so the same wrapper serves all of them.

| Harness | Config file | Egress | Recipe |
|---|---|---|---|
| Claude Code (Tier-1) | `.mcp.json` / `~/.claude.json` | child environment | [claude-code](../guides/recipes/claude-code.md) |
| Cursor (Tier-1) | `.cursor/mcp.json` | HTTP header | [cursor](../guides/recipes/cursor.md) |
| Generic stdio MCP client | client config | child environment | [generic](../guides/recipes/generic.md) |
| Generic HTTP API | client config | HTTP header | [generic](../guides/recipes/generic.md) |
| RFC 8693 target | client config | exchanged token | [generic](../guides/recipes/generic.md) |
| Plain CLI | shell | child environment | [generic](../guides/recipes/generic.md) |

## Honest "not yet"

A harness without a documented interception point is labelled **not yet** (`agentkeys.recipes.RECIPES`
carries `supported=False`), never "supported". See [honest gaps](../explanation/honest-gaps.md).
