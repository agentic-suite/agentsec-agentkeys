# Changelog

All notable changes to agentkeys are documented here. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning: [semver](https://semver.org/) — `0.x` releases are additive-only
([PRD 05 §B / E11](docs/prd/05-features.md)).

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
