# Step-up & recipes design — an approval that is recorded, and Harness A/B (M10)

**Status:** design of record for M10 · **Issue:** #124 (`10.D0`) · **Written before implementation.**
**Sources:** [PRD 18 §5](../../prd/18-issuance-integrity.md), [PRD 05 R9/E8](../../prd/05-features.md),
[PRD 16 §2](../../prd/16-adapters-and-integration.md), [PRD 19](../../prd/19-harness-compatibility.md),
[PRD 17 SC-33–SC-38](../../prd/17-scenarios.md), [egress design](egress.md).

**BLUF:** A higher-class mint (prod by default) cannot happen without an approving decision the broker
**records**: `provenance.decided_by`, `decision`, `authorization.source`. The broker asks agentpolicy
and never decides policy itself; a free-text "approval" from the agent is refused; **timeout = deny**.
The same broker, through the same `agentkeys run` wrapper, serves two Tier-1 harnesses — no fork.

---

## 1. Step-up flow

```
resolve(ref, audience, tool, session)
  └─ class in gated_classes?            (config: step_up.gated_classes, default ["prod"])
       ├─ emit step-up-requested
       ├─ policy.ask(StepUpRequest)     → allow | deny | timeout
       ├─ deny/timeout → emit step-up-denied → ResolutionDenied("step-up-denied: …")
       └─ allow → emit step-up-granted → mint with provenance:
              { "decided_by": <agentpolicy>, "decision": "allow", "source": <authorization.source> }
```

Rules:

1. **No self-approval.** `decided_by` must be a non-empty decision source that is not the requesting
   `agent_id`; a decision string outside `allow|deny|timeout` is a `PolicyError`.
2. **Freshness.** An approval is bound to the request it answered; the idempotent within-window retry
   returns the already-approved issuance without asking again. A new window asks again.
3. **Timeout = deny.** There is no default-allow path (E4).
4. **Provenance is persisted** on the issuance (`provenance_json`), never on the wire as a secret.

`PolicyClient` is a protocol; `AgentPolicyClient` wraps an injected `ask_fn` transport so tests never
touch a network and the broker never invents a decision.

## 2. Recipes

| Recipe | Harness | Config file | Egress |
|---|---|---|---|
| `claude-code` | Claude Code (Tier-1) | `.mcp.json` / `~/.claude.json` | env (stdio server under `agentkeys run`) |
| `cursor` | Cursor (Tier-1) | `.cursor/mcp.json` | HTTP header |
| `generic-mcp` | any stdio MCP client | client config | env |
| `generic-http` | any HTTP API | client config | header |
| `generic-exchange` | RFC 8693 target | client config | exchange |
| `generic-cli` | plain CLI | shell | env |

Every Tier-1 wiring is the **same** shape — `command: agentkeys run --server akref:… -- <server>` with
reference-only `env` — because the broker sits **below** the harness. `validate_wiring` refuses a
wiring whose command is not the broker wrapper, whose `--server` is not a reference, or whose env
carries a secret shape.

**Acceptance harness** — `run_recipe_smoke(recipe, core, …)` resolves through the broker, applies the
recipe's injector (env or header), hands the injection to a target callback, and returns a transcript
that contains only the reference. SC-35/SC-36 pass when the target authenticates the broker-minted
token; a missing/incomplete wiring raises `RecipeError`.

**Honest gap (SC-38):** a harness without an interception point is never labelled "supported"; the
recipe table carries `supported=False` and the docs say "not yet" (PRD 19 labels only).

## 3. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 10.1/10.2 | `tests/test_stepup_approved.py` | approval recorded; provenance + events; TTL honored |
| 10.1/10.2 | `tests/test_stepup_denied.py` | deny and timeout → no credential; self-approval refused |
| 10.3 | `tests/test_harness_recipe_claude_code.py` | wiring valid; authenticated env call; transcript has only the reference |
| 10.4 | `tests/test_harness_recipe_cursor.py` | wiring valid; authenticated header call; same wrapper (no fork) |
| 10.5/10.6 | `tests/test_recipe_acceptance.py` | generic recipes; a broken wiring fails; unsupported harness is "not yet" |

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `10.CR`.
