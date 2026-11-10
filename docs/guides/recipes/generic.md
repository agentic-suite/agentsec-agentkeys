# Recipes: generic MCP, HTTP, RFC 8693, and CLI

> **Status: implemented (M10; SC-37/SC-38).** Smoke: `tests/test_recipe_acceptance.py`.

| Recipe | Use it when | Egress |
|---|---|---|
| `generic-mcp` | any stdio MCP client | child environment |
| `generic-http` | any HTTP API | request header |
| `generic-exchange` | an RFC 8693 token-exchange target | exchanged token |
| `generic-cli` | a plain CLI tool | child environment |

All of them use the broker wrapper `agentkeys run --server akref:… -- <command>` (env) or the header
injector for HTTP; the wiring shape is identical to [Claude Code](claude-code.md) and
[Cursor](cursor.md).

## Custom SDK path

Embedders use the public control surface, not a config file:

```python
from agentkeys.sdk import Broker

resolved = broker.resolve("ref_1", audience="api.example.com", tool="call", session_id="s1")
# resolved.token is the transient scoped token; there is no get_secret()
```

## Honest "not yet"

A harness with no documented interception point is **not** labelled supported. `agentkeys.recipes.RECIPES`
carries `supported=False` for `jetbrains`, `support_label()` prints "not yet", and `validate_wiring`
refuses it (SC-38). Do not add a recipe without a smoke that ends in an authenticated call.
