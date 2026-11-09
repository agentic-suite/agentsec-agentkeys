# Code review log — v0.1.0

**BLUF:** Every milestone closes with a `.CR` work item: review findings are recorded here and resolved
before the milestone gate. This log is **append-only** and **hand-written** — it is evidence, so no
automation writes, rewrites, or summarizes it ([AGENTS.md](../../../AGENTS.md): the hand-maintained-report
rule applies to review findings too). A milestone with an open finding is not closed.

**Status:** Draft — v0.1.0 (2026-11-08) · **Owner:** @deghosal-2026 · **Parent:** agentic-suite #209 · PRD #213

## How findings are recorded

One section per milestone, appended at `.CR`. Each finding: **id · severity (blocker/major/minor) ·
location · what · resolution · status**. A finding stays open until its resolution is a commit ref. A
public-surface finding (a security invariant, a contract, a claim) is a **blocker** — the milestone does not
close until it is resolved or the design is amended to match reality.

## Finding classes we treat as blockers

- A path from any failure to a credential (breaks I2, [PRD 06 §1](../../prd/06-security-baseline.md)).
- A plaintext secret reachable in store/export/ledger/log (breaks I1/I7).
- A replay/forward/widening that succeeds (breaks I4).
- A revocation that is TTL-waiting or policy-gated (breaks I3, D-07).
- A claim that outruns its evidence label ([PRD 20 §6](../../prd/20-standards-and-claims.md)).
- A secret found anywhere by the audit — including **git history** ([Part 8 M15](wbs-v0.1.0-part8-fieldtest-release.md)).

## Findings

### 0.CR — Foundation & identity (2026-11-09)

- **CR-001** · minor · `src/agentkeys/cli.py` · `ArgumentParser.error` overrode a `Never`-returning
  method with `-> None`, so `mypy --strict` failed · fixed: `-> NoReturn` · `757f256` · RESOLVED
- **CR-002** · major · `src/agentkeys/config.py` · nested-key validation errors named only the leaf
  (`path must be a string`) instead of the dotted key, weakening the "actionable error names the failing
  field" NFR · fixed: `_require_*` take a `label` and `store.path` / `clock.skew_tolerance` report dotted ·
  `757f256` · RESOLVED
- **CR-003** · major · `src/agentkeys/config.py` · `ttl = 5` reached `_parse_ttl` and raised
  `AttributeError` (a crash, not a fail-closed denial) · fixed: non-table `ttl` is a `ConfigError` ·
  `757f256` · RESOLVED
- **CR-004** · blocker · `src/agentkeys/config.py` · a literal secret could reach the parse path because
  the pattern scan ran before key validation but a secret in a *list* element (`bindings[].reference`) was
  untested; a gap here would let a secret persist (I1/I7) · fixed: recursive scan covers lists; test
  asserts the secret is rejected and never echoed · `757f256` · RESOLVED
- **CR-005** · minor · `.github/workflows/ci.yml` · the first cut risked being a placeholder that never
  gated coverage; a docs-as-test now asserts every gate step is present · `afc1133`, `757f256` · RESOLVED
- **CR-006** · minor · `Makefile` · targets hard-coded `.venv/bin`, so the same targets could not run in
  CI · fixed: `PYTHON` resolves the venv when present, else PATH · `757f256` · RESOLVED

No open findings. The milestone's public-surface invariants (fail-closed config, references-only,
reserved exit codes, doctor exit precedence) each have a gating test.

<!--
Template:

## 0.CR — Foundation & identity (2026-..-..)

- **CR-001** · blocker · `agentkeys/config.py` · config could fall back to a literal secret on a parse
  ambiguity · fixed: ambiguity is a hard failure with the field named · `abc1234` · RESOLVED
-->
