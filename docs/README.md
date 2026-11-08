# agentkeys docs

Documentation for **agentkeys** — the never-in-context credential broker: agents hold only
*references*, real secrets stay in keychain / credential-file / secret-manager backends, and
short-lived, audience-bound, tool-scoped, session-bound tokens are injected at egress. One command
(`agentkeys revoke`) kills all agent access in ≤1s. Part of the
[agentic-suite](https://github.com/agentic-suite).

> **Status: planned — PRD set being authored from PRD 04 (plan of record).** The requirement set
> (P0 R1–R7, P1 R8–R10, P2 R11–R12) is sourced from the ecosystem research PRD
> (`research/agent-security/ecosystem/prds/213-agentkeys.md`) and is being expanded into this repo's
> own PRD set. Design docs, ADRs, the WBS, and the field-test plan follow as they are authored with
> the build; the PRD set is the plan of record today.

## Sections

| Directory / file | Purpose |
|---|---|
| [prd/](prd/) | Product requirements — why, problem + evidence, requirements P0–P2, harness compatibility, standards, success metrics, non-goals |
| [design/](design/) | Subsystem designs + decisions + threat model (reference model, egress injection, token model, backends, revocation) |
| [reference/](reference/) | CLI, config, token/issuance API, backend matrix, events, errors, limitations |
| [adr/](adr/) | Architecture Decision Records |
| [architecture/](architecture/) | Spec + component architecture (v0.1.0) |
| [wbs/](wbs/) | Work breakdown, by version (index + parts) |
| [plans/](plans/) | Execution plans + testing strategy |
| [field-test/](field-test/) | Field-test plan + report, by version |
| [release/](release/) | Release notes, security audit, claims ledger, verifier |
| [runbooks/](runbooks/) | Operational runbooks (revoke, backend outage, secret-evasion response) |
| [tutorials/](tutorials/) | Hands-on guides |
| [guides/](guides/) | User / operator guide |
| [compliance/](compliance/) | OWASP/ATLAS/NIST/EU/OpenSSF mappings |
| [adapters/](adapters/) | Harness recipes (Claude Code, Cursor, Copilot, Codex CLI, Gemini CLI) and stdio-MCP credential virtualization |
| [examples/](examples/) · [articles/](articles/) · [skills/](skills/) | Samples, posts, operator skills |
| [testing/](testing/) | Test plans (unit, conformance, field-test agents, docker) |

## Start here

- PRD index · Why · Requirements (P0 R1–R7) · Harness compatibility
- Design docs, architecture, ADRs, WBS, runbooks, and tutorials are authored with the build; the PRD
  set is the plan of record today.

## Conventions

- **BLUF** — Bottom Line Up Front in major documents.
- **Honesty** — misses and limitations are documented, not hidden.
- **Versioned directories** — each documentation type is organized by version.
- **Never-in-context** — no doc, example, or screenshot may contain a real credential; use
  references (`env:` / `file:` / backend handle) only.
