# Adoption paths — solo dev → team → CI

**BLUF:** agentkeys is adopted in **stages**, and every stage ends in a *verified brokered call* — never
in a "seems installed." This page is the operational version of the ladder: **Path A** (solo dev, 15
minutes), **Path B** (a team, one afternoon + a policy PR), **Path C** (CI runners and the enterprise
stages). Each path lists its steps, its done-criteria, and what deliberately stays out of scope at that
stage. The deep version of the enterprise ladder is [PRD 23](../prd/23-enterprise-adoption-and-hardening.md).

**Status:** design of record (v0.1.0) — *documented*, not yet *field-tested*.

## Path A — solo developer (15 minutes)

**Who:** Sam (P4). One machine, personal keys, 2–3 harnesses.

1. `pip install agentsec-agentkeys` → `agentkeys init` → `agentkeys doctor` green.
2. `agentkeys scan` — see every secret your agent can read (masked previews).
3. `agentkeys migrate` **one** credential — the one your MCP server uses most.
4. Run the [quickstart](../tutorials/quickstart.md) proofs: context-dump → 0 usable; revoke → replay fails.
5. Leave monitor-safe defaults on. Nothing else to operate.

**Done when:** a real authenticated tool call completed with zero secrets in context, and you watched a
revoke land in under a second on your own machine.

**Deliberately out of scope at this stage:** migrating every secret, policy, CI, posture reporting. Adopt
one credential, verify the invariant, keep going if it earned trust.

## Path B — a team (an afternoon + one policy PR)

**Who:** Maya (P1) + Ravi (P2). Shared repos, shared harnesses, a real prod boundary.

1. **Config-as-code:** the `agentkeys` config goes in the repo (it contains references and backend ids,
   never secrets — by construction). Config review is a normal PR review.
2. **Migrate the shared surface:** run `agentkeys scan` in CI-ready mode; the team's `.env`/`mcp.json`
   entries become references with named owners. Exceptions go on an explicit list, not in a drawer.
3. **Step-up policy (the prod boundary):** in [agentpolicy](https://github.com/agentic-suite), mark
   prod-class credentials `ask`. From then on a prod-class mint is *impossible* without an approving
   human decision ([R9](../prd/05-features.md)); timeout = deny.
4. **Evasion monitoring:** leave monitor mode on; `evasion-detected` events flow to agentwatch. Blocking
   composes later with agentkernel/agentseatbelt.
5. **The drill:** once a quarter, run the revoke drill and record it by hand ([rb-7](../prd/22-operations-and-governance.md)).

**Done when:** no literal secret has been merged in a quarter (or every exception is on the explicit
list), the prod class is step-up-gated, and one drill is recorded.

**What this stage buys:** the Replit sentence stops being possible — a destructive action with a
production credential cannot even *authenticate* without a human approving the token.

## Path C — CI runners and the enterprise stages

**Who:** platform/security teams. Read [PRD 23](../prd/23-enterprise-adoption-and-hardening.md) for the
full ladder (Stage 0–4); the operational highlights:

- **CI runners (today's shape):** a broker per runner, credentials from the runner's backends
  (cloud secret managers at [R10](../prd/05-features.md)). The ledger + exit codes give the pipeline a
  real credential gate; "kill the runaway CI agent" becomes `agentkeys revoke --agent <ci-agent>`.
- **Fleet (R11):** central broker, delegation that only ever **narrows**, per-team policy namespaces.
- **Identity (R12):** SPIFFE/WIMSE SVIDs as actor tokens — the Aembit shape, OSS-ified.
- **Certifications (Stage 4):** the evidence pipeline started at Stage 0; the auditor arrives to
  artifacts that already exist.

**Done when (Stage 2+):** fleet revoke drill green, delegation proven monotonically narrowing, and the
gap matrix still leading the buyer packet.

## The one rule across all paths

**Never bridge a failure with a literal secret.** Locked keychain, missing backend, CI hiccup — the fix
is never pasting the key back in. Fail-closed is the product; convenience that reintroduces the secret is
the bug we exist to remove ([PRD 14 §4](../prd/14-non-goals.md)).

## Related

- [Quickstart](../tutorials/quickstart.md) · [Demo scripts](demo-scripts.md) ·
  [Operations & governance](../prd/22-operations-and-governance.md) ·
  [The adoption ladder](../prd/23-enterprise-adoption-and-hardening.md)
