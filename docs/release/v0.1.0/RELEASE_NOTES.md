# agentkeys 0.1.0 — release candidate

**Status: not released.** These notes describe the `v0.1.0` release candidate; the tag lands only after the
release gates are green ([RELEASE_PLAN.md](RELEASE_PLAN.md)) and the milestone is signed off.

*Revoke the agent, not the quarter.* The never-in-context credential broker for AI agents: agents hold only
**references**, secrets stay in the keychain / credential file, short-lived audience-bound tokens are injected
**at egress** — and one command kills all of an agent's access in **≤1 second**, replay-verified.

---

## What this release does

- **Reference-only context** — a config carries `akref:` handles, never a value; a literal secret in config is
  an error, not a stored secret.
- **Egress-only injection** — child environment, HTTP header, and RFC 8693 token exchange.
- **Bound tokens** — audience (one server), tool (one operation), session (dies with the conversation),
  short TTL, single use.
- **`revoke` ≤1s, replay-verified** — revoke is a CAS on `revoke_epoch`; `replay --last` proves the refusal.
- **stdio MCP virtualization** — a stock stdio server authenticates under the broker with references in its
  config and a scoped token at its egress; the co-located-runtime limit is documented, not hidden.
- **Hash-chained ledger** — every issuance, use, upgrade and revocation is an append-only transition plus its
  `agentwatch`-schema event; `export` and `verify-log` never emit a secret.
- **`scan` / `migrate`** — find candidate secrets (masked), move one to a backend, rewrite its use sites.
- **Fail-closed** — an unavailable or ambiguous backend denies issuance; never a static fallback.
- **Supply-chain floor** — stdlib-only runtime, `security.txt`, CycloneDX SBOM, CI gates.

## Field-test evidence (M14)

The verdicts come from the **hand-maintained** report — [FIELD_TEST_REPORT.md](../../field-test/v0.1.0/FIELD_TEST_REPORT.md) —
entered by hand from committed results, never generated:

| | |
|---|---|
| Verdicts | **71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN** across 74 cases |
| Blocking scenarios | **all five PASS** — FT-RK-KILLTIME, FT-AP-CONTEXTDUMP, FT-AP-TAMPER, FT-AP-EVIDENCE, FT-MP-SCANMIGRATE |
| Kill-time | p50 0.012ms · p95 0.017ms · max 0.031ms at N=100/scope; 100/100 replays refused |
| Context dump | 0 usable credentials; the seeded falsification control fires |
| scan/migrate | 100% recall on the seeded fixture, 0 printed values |

Published benchmark: [bench/README.md](../../../bench/README.md) — a third party can re-run it, which is what
would move a claim from *field-tested* to *verified*.

### The three WARNs (each with its limitation)

| Case | Why it is not a PASS |
|---|---|
| **FT-CL-FIRST** | the scripted median (0.54s) and a fresh-venv path (2.7s) are green, but **no naive human on a fresh machine** has been measured |
| **FT-HC-CLAUDE** | `claude` 2.1.187 is installed and the wiring+smoke legs are green; the live headless run is blocked — `Not logged in · Please run /login` |
| **FT-HC-CURSOR** | the recipe ships, but Cursor is a GUI IDE with **no headless CLI surface** on the test box |

One WARN was *removed* rather than argued with: `FT-EV-ENFORCE` is a PASS because a real filesystem-deny
enforcer was composed (`chmod 000` plus a verifier that raises if the file is readable). One FAIL appeared
during the sweep (`FT-DK-AIRGAP`, a harness volume-ownership defect); it was fixed and re-ran green, and the
fail → fix → green arc stays in the report.

**Nothing is verified.** *Verified* means an independent third party reproduced the claim — no one has re-run
`bench/` yet, so no row wears that label ([CLAIMS.md](CLAIMS.md)).

## Honest gaps (day one)

From [PRD 23 §1](../../prd/23-enterprise-adoption-and-hardening.md) and [PRD 03 §4](../../prd/03-landscape.md):

| You might expect | What v0.1.0 actually gives you |
|---|---|
| SSO / SCIM / directory sync | **not yet** — local OS principal; identity consumed at R12 |
| Multi-tenant, RBAC, WORM retention | **not yet** — single-user store; retention is explicit and local |
| SOC 2 / ISO 27001 / ISO 42001 | **mappings only** — not a certification (see the non-claims) |
| Central fleet control | **not yet** — every machine runs the same local semantics |
| Cloud backends (1Password, Vault, K8s, cloud SM) | **not yet** — keychain + file only at v0.1.0 |
| Windows | **not supported** — macOS + Linux first; the CLI says so |
| Proof-of-possession (DPoP) | **not yet** — bearer tokens until R14 |
| Protection from a co-located same-runtime process | **not protectable** — documented boundary ([PRD 06 §4](../../prd/06-security-baseline.md)) |
| Injection *detection* | **not claimed** — we mitigate architecturally, never assert a detection rate |

Harness coverage is honest too: Claude Code and Cursor are **documented** (wired, smoke-tested, live leg
blocked); Copilot is **lower-layer**; Codex CLI, Gemini CLI and Windows are **not yet**. See
[COMPATIBILITY.md](COMPATIBILITY.md).

## Release gates (all green before the tag)

- **Security audit** — 0 verified secrets in the tree and in the full history, dual-scanner, planted-fake
  control fired: [SECURITY_AUDIT.md](SECURITY_AUDIT.md)
- **Claims lint** — 18 claims, 0 over-claims, 0 verified: [CLAIMS_LINT.md](CLAIMS_LINT.md)
- **Compatibility matrix** — generated, no "supported" without a green pack: [COMPATIBILITY.md](COMPATIBILITY.md)
- Tests, coverage ≥95%, `ruff`, `mypy --strict`, review log, docs — recorded in the milestone checkpoint.

## Upgrading

First release: there is no previous version to migrate from. If you have credentials in `.env` files, run
`agentkeys scan` (masked output) and `agentkeys migrate` to move one to a backend; the quickstart replays the
full journey in a fresh virtualenv.

## Non-claims

Not a compliance certification · not an injection detector · not proof-of-possession · not protection from a
process sharing the agent's readable runtime · not an identity provider · not a vault.
