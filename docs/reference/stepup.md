# Step-up reference — approvals recorded, not assumed

> **Status: implemented (M10).** Design: [step-up & recipes design](../design/step-up-recipes.md).

## Configuration

```toml
[step_up]
gated_classes = ["prod"]      # default when the table is absent
timeout_seconds = 30          # recorded intent; timeout = deny
policy = "agentpolicy"        # informational label for the decision source
```

An empty `gated_classes` list is refused at load. Absence of `[step_up]` keeps prod gated (R9).

## Flow

1. `ResolutionCore` resolves the reference and binding, then checks whether the reference's class is gated.
2. Gated: `step-up-requested` → `PolicyClient.ask(StepUpRequest)` → one of `allow | deny | timeout`.
3. `allow` → `step-up-granted`, then mint with `provenance = {decided_by, decision, source}`
   (persisted as `provenance_json`; the issuance document exposes it as `provenance`).
4. `deny`/`timeout`/invalid decision → `step-up-denied` (warn) and `ResolutionDenied("step-up-denied: …")`.
   No issuance, no token.

`AgentPolicyClient(ask_fn)` validates the answer: the verdict must be one of `allow|deny|timeout`, must
name a `decided_by` source, must carry `authorization.source`, and `decided_by` may not equal the
requesting `agent_id` (no self-approval). An idempotent retry inside the issuance window returns the
already-approved issuance without asking again; a new window asks again.

## Recipes

[`docs/guides/recipes/`](../guides/recipes/claude-code.md): `claude-code`, `cursor`, `generic-mcp`,
`generic-http`, `generic-exchange`, `generic-cli`. Every MCP recipe is the same wrapper —
`command: agentkeys run --server akref:… -- <server>` with reference-only `env` — because the broker sits
below the harness. `jetbrains` is labelled **not yet** (no documented interception point).

```bash
python -m pytest tests/test_harness_recipe_claude_code.py tests/test_harness_recipe_cursor.py
```
