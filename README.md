# agentkeys

> **Revoke the agent, not the quarter.** The never-in-context credential broker for AI agents: agents hold
> only *references*, real secrets stay in your keychain / credential files / vault, short-lived
> audience-bound tokens are injected **at egress** — and one command kills all of an agent's access in
> **≤1 second**, replay-verified in CI.

[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/agentic-suite/agentsec-agentkeys/badge)](https://scorecard.dev/viewer/?uri=github.com/agentic-suite/agentsec-agentkeys)

Part of the [agentic-suite](https://github.com/agentic-suite) — open-source, harness-agnostic security
for AI agents. Apache-2.0.

## Status

**in progress — the broker core is built through M13; field tests and release (M14/M15) are next.** The
full requirement set ([PRD 00–23 + Appendix A](docs/prd/README.md)) and the build plan
([v0.1.0 WBS — 16 milestones, M0–M15](docs/wbs/v0.1.0/wbs-v0.1.0-index.md)) are public on purpose, so we can
be held to them. Implemented: reference/issuance contracts, the store, keychain/file backends, egress
injection (env/header/RFC 8693), stdio virtualization, `revoke`/`replay`, the hash-chained ledger with
`export`/`verify-log`, `scan`/`migrate`, evasion/tamper detection, step-up approvals and harness recipes,
the conformance kit, backup/restore, and `serve`. Not yet: `init`, `context-dump`, `scan-usable`, keychain
migration, signed releases, and the M14 field test — see [honest gaps](docs/explanation/honest-gaps.md).
No release has shipped; claims stay at their evidence label
([evidence labels](docs/prd/20-standards-and-claims.md)).

## Install & run (v0.1.0 foundation)

```sh
pip install agentsec-agentkeys   # stdlib-only, no runtime dependencies
agentkeys --version              # agentkeys 0.1.0
agentkeys --help                 # the frozen v0.1.0 command surface
agentkeys doctor                 # read-only health check: 0 healthy · 2 denied · 3 tamper
```

Configuration lives under `AGENTKEYS_HOME` (default `~/.agentkeys`) in `config.toml`. It carries
**references only** — a literal secret in config is an error, never stored and never printed. See the
[foundation design](docs/design/v0.1.0/foundation.md) and the [CLI reference](docs/reference/cli.md).

### Reserved exit codes (stable within v0.x)

| Code | Meaning |
|---|---|
| `0` | success (and for `scan-usable`: **0 usable credentials** — the invariant holds) |
| `1` | usage or internal error |
| `2` | **denied** — fail-closed denial with a reason |
| `3` | **tamper detected** — integrity check failed |
| `4` | **revoke verified** — the replay was refused |

`scan`, `migrate`, `ref`, `run`, `revoke`, `replay`, `export`, `verify-log`, `conformance`, `serve`,
`backup`, and `restore` are implemented; `init`, `context-dump`, and `scan-usable` remain honest stubs that
exit non-zero and name the milestone. The [quickstart](docs/tutorials/quickstart.md) is replayed by a step
test (`tests/docs/test_quickstart.py`).

**Platforms:** macOS and Linux. **Windows is not supported** — the CLI says so rather than failing
cryptically.

## The problem

The most dangerous string in your agent's context isn't the prompt — it's the **API key in its
environment**: static, long-lived, over-scoped, no audience binding, no kill switch. Prompt injection
exfiltrating production keys is documented in the wild, and when it happens, "revoke" means rotating the
credential across every system it touches. **A quarter of work for what should be one command.**

## What agentkeys does

| | |
|---|---|
| **Never-in-context** | Agents hold opaque `akref:` references — safe to log, print, and leak. A full context-dump attack pack must find **zero usable credentials**; it runs in CI as a permanent invariant. |
| **Egress-only injection** | Real credentials resolve at the moment of use and inject at egress — child-process env (stdio MCP), HTTP header, or RFC 8693 token exchange. The agent's transcript never contains the secret. |
| **Bound tokens** | Every token is short-lived, **audience-bound** (RFC 8707), **tool-scoped**, and **session-bound**. Replay it anywhere else — it fails, and the attempt is logged. |
| **Revoke ≤1s** | `agentkeys revoke <agent\|session\|all>` — the next exchange refuses, issued tokens stop authenticating. Measured end-to-end (issue → revoke → replay fails), continuously in CI. |
| **stdio MCP virtualization** | The flagship nobody covers: local stdio MCP servers launched under the broker, credentials supplied at call time — no secret in `mcp.json`, env, or transcript. |
| **scan / migrate** | `agentkeys scan` finds the secrets your agents can read (`.env`, `mcp.json`, scripts); `agentkeys migrate` moves one into the keychain and rewrites every use site to a reference. |
| **Step-up approvals** | Prod-class scope is *impossible* to mint without an approving human decision (via agentpolicy); timeout = deny. |
| **Evidence-grade audit** | Every issuance/use/upgrade/revocation lands in a hash-chained local ledger + agentwatch events — a credential lifecycle an auditor reconstructs per session. |
| **Fail closed, everywhere** | Locked keychain, corrupt store, offline sink — every failure is a denial, never a fallback to a static secret. |

## The 60-second demo (the designed v0.1.0 experience)

```sh
$ agentkeys scan
Found 3 candidate secrets (masked previews only):
  .env                    AWS_SECRET_ACCESS_KEY     ***…7f2a   broad-reuse: 2 sites
  .mcp.json               GITHUB_TOKEN              ***…9c11   static, in agent-readable config
  scripts/deploy.sh       NPM_TOKEN                 ***…4b0d

$ agentkeys migrate .mcp.json GITHUB_TOKEN --backend keychain
✔ moved to keychain item "agentkeys/dev/github-pat"
✔ rewrote .mcp.json → "GITHUB_TOKEN": "akref:keychain/agentkeys/dev/github-pat"
✘ original value deleted from config; present nowhere except the backend

$ claude   # the agent runs; the MCP server authenticates via the broker
…tool call succeeds — transcript contains only the reference…

$ agentkeys context-dump --session latest | agentkeys scan-usable
0 usable credentials found in transcript/env/args/config/logs ✔

$ agentkeys revoke --agent claude-code && agentkeys replay --last
revoked in 0.19s · replay of pre-revoke token: REFUSED (exchange-rejected)
```

*(Commands are the designed CLI — the plan of record. Every line above maps to a gated scenario:
[SC-51](docs/prd/17-scenarios.md), [SC-12](docs/prd/17-scenarios.md), [SC-40](docs/prd/17-scenarios.md),
[SC-24](docs/prd/17-scenarios.md).)*

## Why not X?

- **Why not just 1Password / Doppler / Infisical?** Use them — **as backends**. They store secrets well;
  they don't virtualize stdio MCP, unify per-tool/session token models across your whole agent surface,
  or publish a ≤1s kill. agentkeys makes *your* vault never-in-context. ([FAQ](docs/prd/00-press-release.md))
- **Why not Aembit / Entra Agent ID?** Excellent — and enterprise control planes. agentkeys is the OSS,
  local-first, stdio-inclusive end; later, a standards-native client of the same control planes.
- **Another injection detector?** No. We don't classify prompts; we make injection **not worth it** —
  there is nothing usable in the context to steal. ([Why brokers, not detectors](docs/explanation/why-brokers-not-detectors.md))

## Compatibility (below the harness, by construction)

| Harness | v0.1.0 | v0.3.0 |
|---|---|---|
| Claude Code | ✅ recipe #1 (first) | ✅ |
| Cursor | ✅ recipe #2 | ✅ |
| GitHub Copilot (agent mode) | documented lower-layer coverage | ✅ |
| OpenAI Codex CLI | not yet | ✅ |
| Gemini CLI | not yet | ✅ |
| Generic MCP clients / SDKs | ✅ by construction | ✅ |

Verified, not asserted: a harness is "compatible" when its attack pack passes in CI
([PRD 19](docs/prd/19-harness-compatibility.md), [PRD 16](docs/prd/16-adapters-and-integration.md)).

## Documentation

### PRD — the plan of record (00–23 + Appendix A)

- **[PRD index](docs/prd/README.md)** — the full set, with the reading order per audience
- **Pitch:** [Press release / FAQ](docs/prd/00-press-release.md) · [Why](docs/prd/01-why.md) · [Landscape](docs/prd/03-landscape.md)
- **Build:** [Architecture](docs/prd/02-architecture.md) · [Features R1–R19 + E1–E15](docs/prd/05-features.md) · [Data model](docs/prd/15-data-model.md) · [Adapters & integration](docs/prd/16-adapters-and-integration.md)
- **Trust:** [Security baseline](docs/prd/06-security-baseline.md) · [Issuance integrity](docs/prd/18-issuance-integrity.md) · [Standards & claims](docs/prd/20-standards-and-claims.md) · [Evidence & method](docs/prd/21-evidence-register-and-method.md)
- **Deliver:** [Roadmap](docs/prd/09-roadmap.md) · [Operations & governance](docs/prd/22-operations-and-governance.md) · [Enterprise adoption](docs/prd/23-enterprise-adoption-and-hardening.md) · [Traceability](docs/prd/12-traceability.md)
- [Appendix A — consolidated source PRD](docs/prd/appendix-a-consolidated-prd.md) (the vault PRD verbatim, every line traced)
- Guides: [Quickstart (designed)](docs/tutorials/quickstart.md) · [Adoption paths](docs/guides/adoption-paths.md) · [Demo scripts](docs/guides/demo-scripts.md) · [Why brokers, not detectors](docs/explanation/why-brokers-not-detectors.md) · [CLI](docs/reference/cli.md) · [Glossary](docs/reference/glossary.md) · [Control-coverage matrix](docs/compliance/control-coverage-matrix.md)

### WBS — the build plan for v0.1.0 (16 milestones, M0–M15, across 8 parts)

- **[WBS index](docs/wbs/v0.1.0/wbs-v0.1.0-index.md)** — milestones, the standard gates, and the requirement → CUJ → scenario → milestone trace
- [Part 1 — Foundation & BrokerStore (M0–M1)](docs/wbs/v0.1.0/wbs-v0.1.0-part1-foundation-store.md)
- [Part 2 — Contracts & Backends (M2–M3)](docs/wbs/v0.1.0/wbs-v0.1.0-part2-contracts-backends.md)
- [Part 3 — Egress & the stdio Flagship (M4–M5)](docs/wbs/v0.1.0/wbs-v0.1.0-part3-egress-stdio.md)
- [Part 4 — Revocation & Evidence (M6–M7)](docs/wbs/v0.1.0/wbs-v0.1.0-part4-revoke-ledger.md)
- [Part 5 — Hygiene & Hardening (M8–M9)](docs/wbs/v0.1.0/wbs-v0.1.0-part5-scan-evasion.md)
- [Part 6 — Approvals & Assurance (M10–M11)](docs/wbs/v0.1.0/wbs-v0.1.0-part6-stepup-conformance.md)
- [Part 7 — Operations & Docs (M12–M13)](docs/wbs/v0.1.0/wbs-v0.1.0-part7-ops-docs.md)
- [Part 8 — Field Test & Release (M14–M15)](docs/wbs/v0.1.0/wbs-v0.1.0-part8-fieldtest-release.md) — the final two milestones (field tests + release readiness, incl. the `trufflehog` + git-history security audit that gates the tag)
- [Code review log](docs/wbs/v0.1.0/codereview-log.md)

## Roadmap (one headline per release, gate or no release)

| Release | Headline | Gate |
|---|---|---|
| **v0.1.0** | The complete never-in-context lifecycle + stdio flagship + scan/migrate | kill-time ≤1s in CI; 0 usable secrets; fail-closed matrix; ≥2 Tier-1 recipes |
| **v0.1.x** | Enterprise/cloud backends + posture report | conformance-gated backends; posture on real machines |
| **v0.2.0** | Server/HA fleet broker + SPIFFE/WIMSE identity | monotonic delegation; cluster-safe store |
| **v0.3.0** | Product depth: budgets, DPoP, attestation, taint, canaries; all 5 harnesses; MCP ext-auth landed | full v0.3.0 gate ([PRD 09](docs/prd/09-roadmap.md)) |

## The ecosystem

agentkeys is the hands on the keys in [agentic-suite](https://github.com/agentic-suite):
[agentwatch](https://github.com/agentic-suite) owns the event schema · agentpolicy decides approvals ·
agenthalt triggers revocations · agentdrill measures kill times · agentcomply turns the ledger into
evidence.

## Contributing & security

[CONTRIBUTING.md](CONTRIBUTING.md) (test-first, one ticket at a time, DCO signed) ·
vulnerabilities go to [SECURITY.md](SECURITY.md), never a public issue.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
