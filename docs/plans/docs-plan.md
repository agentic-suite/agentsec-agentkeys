# Docs plan — v0.1.0

**BLUF:** every page a stranger needs to install, use, operate, and honestly evaluate v0.1.0, mapped
to the requirement it serves. Docs are tested: the CLI/config coverage test fails on an undocumented
flag or key, and the quickstart's exact commands are replayed by a step test.

- **Milestone:** docs (WBS part — security & docs; authored with the build)
- **Requirements:** PRD 04 §P0 R1–R7, harness compatibility (≥2 Tier-1 at v0.1.0)

## Page inventory

| Page | Requirement | Acceptance |
|---|---|---|
| `docs/tutorials/quickstart.md` | R2, R5 | step test completes install → first brokered authenticated tool call where the agent never sees the secret |
| `docs/reference/cli.md` | R4 | every command + option documented (`revoke`, issue, inspect, backend) — coverage test |
| `docs/reference/config.md` | R5 | every config key + backend selection + fail-closed behavior documented — coverage test |
| `docs/reference/tokens.md` | R3 | token model field table: TTL, audience binding, tool scope, session binding |
| `docs/reference/backends.md` | R5 | backend matrix (keychain, credential file) + failure semantics |
| `docs/reference/events.md` | R6 | credential-lifecycle event fields + `agentwatch`-schema mapping |
| `docs/reference/security.md` | R1, R7 | never-in-context invariant + secret-evasion detection surface |
| `docs/reference/scan-migrate.md` | R17 | every `scan`/`migrate` flag + the never-print-a-secret safety rules (coverage test) |
| `docs/reference/posture.md` | R18 | every posture finding class + the JSON schema documented |
| `docs/guides/adoption-paths.md` | CUJ-1, CUJ-14 | each staged path ends in a verified brokered call |
| `docs/guides/demo-scripts.md` | GTM | each demo maps to scenarios and runs green |
| `docs/explanation/why-brokers-not-detectors.md` | PRD 01 | the explainer: why architecture beats detection |
| `docs/adapters/harness-recipes.md` | compatibility | each recipe ends in a verified authenticated call for that harness |
| `docs/guides/operator-guide.md` | R4 | issue → use → revoke; reading the lifecycle audit |
| `README.md` | everyone | install/usage live; status reflects the built core |

## Step-test protocol

1. Fresh `AGENTKEYS_HOME` under a temp directory; `init` exactly as the quickstart says.
2. Put a backend secret in place via `agentkeys scan` + `agentkeys migrate` (keychain item or credential
   file) — never in agent env.
3. Run the documented harness recipe; assert the tool call authenticates while the agent process
   observed only a reference.
4. Assert `agentkeys revoke` returns the service to unauthenticated within the ≤1s budget.

## Honesty rules

- No page claims a capability the code does not have; unsupported rows say so.
- Field-tested labels only come from the hand-maintained report; plan pages use
  conformance/documented labels.
- A page that cannot be tested is listed as a limitation, not marked done.
