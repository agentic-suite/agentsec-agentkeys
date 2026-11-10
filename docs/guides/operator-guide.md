# Operator guide — issue → use → revoke

> **Status: implemented (M6–M13).**

1. **Configure** references only — see the [config reference](../reference/config.md).
2. **Register** a reference (`agentkeys ref list` shows what the broker can resolve; never a value).
3. **Use** it through a recipe — `agentkeys run --server akref:… -- <command>` injects the scoped token in
   the child's environment at egress ([recipes](../adapters/harness-recipes.md)).
4. **Revoke** — `agentkeys revoke --session ID` (or `--agent`, `--all`) is a CAS on the session epoch.
5. **Prove it** — `agentkeys replay --last` exits `4` only when the pre-revoke resolution is refused.
6. **Read the lifecycle** — `agentkeys export --session ID` (deterministic JSONL) and
   `agentkeys verify-log` (chain integrity; exit `3` on tamper).
7. **Operate** — backup/restore, serve lock, and drills are in the [ops reference](../reference/ops.md) and
   the [runbooks](../runbooks/rb-1-locked-backend.md).
