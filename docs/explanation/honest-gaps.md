# Honest gaps — what v0.1.0 does not do

> **Status: field-tested (M14 complete).** Claims follow the PRD 20 vocabulary. The verdicts below come from
> the **hand-maintained** [field-test report](../field-test/v0.1.0/FIELD_TEST_REPORT.md) — entered by hand
> from committed results, never generated. **71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN** across 74 cases.

## Not implemented in v0.1.0

| Area | Gap | Status |
|---|---|---|
| `agentkeys init`, `context-dump`, `scan-usable` | still honest stubs — each exits non-zero and names its milestone (the quickstart writes the config directly) | not yet |
| `migrate --backend keychain` | only the `0600` file backend is implemented; keychain migration refuses honestly | not yet |
| `scan --ci` | scheduled for v0.1.x; refuses as not-yet | not yet |
| OS-level evasion enforcer | `enforce` blocks only where an enforcer composes; `FT-EV-ENFORCE` now **passes** because one was composed (`chmod 000` + a verifier that raises if the file is readable) | limitation |
| RFC 9449 DPoP | deferred to v0.3.0 (R14) | not supported |
| Enterprise backends (Vault/1Password/cloud SM) | v0.1.x (R10); an unknown driver refuses | not supported |
| Sigstore/SLSA signing + provenance | **blocked** on release credentials — the SBOM is generated and the tag must carry this stated limitation rather than claiming a signed release | blocked |
| Live harness field runs | Claude Code is wired and smoke-tested but the headless run is blocked (`Not logged in · Please run /login`); Cursor has no headless surface | WARN (named) |
| Install → first call, naive human on a fresh machine | the scripted median (0.54s) and a fresh-venv path (2.7s) are green; no naive-human fresh-machine median exists | WARN (named) |
| Copilot / Codex CLI / Gemini CLI | Copilot is **lower-layer coverage** (closed hook surface); Codex and Gemini are **not yet** | lower-layer / not yet |
| Cloud/HA server mode | R11 (v0.1.x) | not supported |

## The three remaining WARNs

Each is a genuine, named limitation — not a rounded pass:

- **FT-CL-FIRST** — the install path is measured three ways (scripted median, a fresh venv, the full
  quickstart at 2.7s), but nobody has timed a naive human on a fresh machine.
- **FT-HC-CLAUDE** — `claude` 2.1.187 is installed and the wiring + smoke legs pass; the live headless call
  returns `Not logged in · Please run /login`.
- **FT-HC-CURSOR** — the recipe ships, but Cursor is a GUI IDE with no headless CLI surface on the test box.

## What v0.1.0 does claim (with evidence)

| Claim | Label | Evidence |
|---|---|---|
| References in context, secrets only at egress | field-tested | [FT-CL-ENV](../../field-test/v0.1.0/results/FT-CL-ENV/summary.md), injector tests |
| Audience/tool/session bindings, single use, replay refused | field-tested | FT-BR-AUDIENCE / TOOL / SESSION / STALE |
| Revoke ≤1s end-to-end, replay-verified | field-tested | FT-RK-KILLTIME — p95 0.017ms, max 0.031ms, 100/100 replays refused |
| A full context dump yields 0 usable credentials | field-tested | FT-AP-CONTEXTDUMP (seeded control fires) |
| Hash-chained ledger, `export`, `verify-log` | field-tested | FT-LA-EVENT / EXPORT / NOSECRET / TAMPER |
| `scan`/`migrate`: 100% recall, 0 printed values | field-tested | FT-MP-SCANMIGRATE |
| stdio child authenticates with no secret in config/env/transcript | field-tested | FT-ST-NOSECRET, FT-DK-BOUNDARY |
| Fail-closed on every operational failure | field-tested | FT-FC-* 6/6 |
| RFC 8693/8707/9700/9728/9068/7636 conformance | conformance | FT-CONF-STANDARDS (DPoP explicitly not supported) |

The complete, machine-checked list is the [claims ledger](../release/v0.1.0/CLAIMS.md) — 18 claims, 0
over-claims, **0 verified**.

## Field-test labels

A scenario is *field-tested* only when a human records its verdict in
`docs/field-test/<version>/FIELD_TEST_REPORT.md`. No automation writes that report, and the guard against it
is itself a field case (`FT-HONESTY-REPORT`).
