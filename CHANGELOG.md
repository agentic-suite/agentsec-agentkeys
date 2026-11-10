# Changelog

All notable changes to agentkeys are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [semver](https://semver.org/) — `0.x` releases are additive-only
([PRD 05 §B / E11](docs/prd/05-features.md)).

## [0.1.0] — 2026-11-10

**Unsigned release.** No Sigstore signature and no SLSA provenance — verify by SBOM, checksums, and a re-run of
`python -m agentkeys.release audit --root .`.

### Added

- **Never-in-context brokering**: agents hold `akref:` references; the secret is injected only at egress
  (child env, HTTP header, RFC 8693 exchange) and never rendered into context, args, or logs.
- **Bound issuance**: audience (one server), tool (one operation), session (dies with the conversation),
  short TTL, single use.
- **`revoke` + `replay`**: `revoke` is a CAS on `revoke_epoch`; `replay --last` proves the refusal. Measured
  end-to-end: p50 0.012ms · p95 0.017ms · max 0.031ms at N=100 per scope, 100/100 replays refused.
- **stdio MCP credential virtualization**: a stock stdio server authenticates under the broker with references
  in its config; the co-located-runtime limit is documented, not hidden.
- **Hash-chained lifecycle ledger** with secret-free `export` and `verify-log` recomputation.
- **`scan` / `migrate`**: 100% recall on the seeded corpus, 0 printed values.
- **Fail-closed by default**, stdlib-only runtime, keychain + file backends, step-up issuance, backup/restore,
  `serve`, and a standards conformance kit (RFC 8693/8707/9700/9728/9068/7636).
- **Release tooling**: `python -m agentkeys.release {audit,claims,compat,sbom}` — the secret-leakage audit, the
  claims lint, the generated compatibility matrix, and the SBOM.

### Evidence

- Field test (hand-verdict, M14): **71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN** over 74 cases; all five blocking
  scenarios PASS. The three WARNs are named limitations: no naive-human fresh-box install median; Claude Code
  not logged in headlessly; Cursor has no headless CLI surface.
- Secret-leakage audit: 0 verified in the tree and in the full history. Claims lint: 18 claims, 0 over-claims,
  **0 verified**. Compatibility: no "supported" without a green pack.

### Known gaps

`init`, `context-dump`, `scan-usable` are honest stubs; keychain migration, `scan --ci`, DPoP, cloud backends,
fleet control and Windows are not yet. See [honest gaps](docs/explanation/honest-gaps.md).

### Not done

- **Not published to PyPI yet** — the upload needs a maintainer credential (never a token pasted into a chat).
- **Not signed** — by decision, stated everywhere.

## [Unreleased]

### Added — plan of record (no code yet)

- **PRD set complete (00–23 + Appendix A)** — the published requirements the build is held to:
  never-in-context references (R1), egress-only injection across stdio-env / HTTP header / RFC 8693
  exchange (R2), audience/tool/session bindings (R3), revoke ≤1s replay-verified (R4), keychain + file
  backends fail-closed (R5), hash-chained lifecycle ledger (R6), secret-evasion detection (R7),
  **stdio MCP credential virtualization** (R8, the coverage-row-#8 flagship), step-up issuance (R9),
  and `agentkeys scan`/`migrate` (R17).
- **Docs**: architecture, security baseline (incl. the "we are a target" threat model), issuance
  integrity (the identity chain), adapters & recipes, operations & governance (8 runbooks), enterprise
  adoption ladder, scenarios (SC-01…SC-53), evidence & method (context-dump + kill-time protocols),
  standards & claims (RFC 8693/8707/9700/9728/9068, MCP ext-auth contribution plan, WIMSE/AIMS track),
  OWASP/ATLAS/NIST control-coverage matrix, glossary, CLI surface, quickstart, adoption paths, demo
  scripts, and the why-brokers-not-detectors explainer.
- **Governance**: AGENTS.md (hand-maintained field-test-report rule), CONTRIBUTING.md (test-first, DCO).

### Notable commitments this changelog will be held to

- The first `[0.1.0]` entry may only appear when the v0.1.0 exit gate passes
  ([PRD 09 §3](docs/prd/09-roadmap.md)): kill-time ≤1s in CI, 0 usable secrets in the context-dump,
  fail-closed matrix 100%, ≥2 Tier-1 recipes, signed release + SBOM.
- Evidence labels travel with every claim: *documented → conformance → field-tested → verified*
  ([PRD 20 §6](docs/prd/20-standards-and-claims.md)) — nothing ships wearing a label it didn't earn.
