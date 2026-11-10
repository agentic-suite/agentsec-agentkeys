# Conformance, evidence, invariants, and supply chain (M11)

**Status:** design of record for M11 · **Issue:** #136 (`11.D0`) · **Written before implementation.**
**Sources:** [PRD 20 §1/§5](../../prd/20-standards-and-claims.md), [PRD 21](../../prd/21-evidence-register-and-method.md),
[PRD 05 E5/E13/E15](../../prd/05-features.md), [PRD 17 §13](../../prd/17-scenarios.md), [PRD 06 §1](../../prd/06-security-baseline.md).

**BLUF:** the product must be **provable**, not asserted. `agentkeys conformance` runs the standards and
backend suites and refuses to imply an unsupported standard; the evidence scanner proves no secret-shape
material sits in the store, ledger, or export; every invariant has a fixture that goes **red when it is
violated**; the attack packs run as release-blocking regressions; and the repository's own supply chain is
checked (empty runtime deps, `security.txt`, an SBOM, CI gates). Anything that needs signing credentials is
labelled honestly and deferred to M15.

---

## 1. Conformance suites

| Suite | What it checks | Status |
|---|---|---|
| `rfc8693` token exchange | `audience`, `scope`=tool, `subject_token`=broker secret, `actor_token` present, client token absent | aligned |
| `rfc8707` resource indicators | wrong-audience injection refused at the injector | aligned |
| `rfc9700` security BCP | TTL inside the class ceiling, single-use, no client-token passthrough | aligned |
| `rfc9728` protected-resource metadata | an https (or localhost) `/.well-known/oauth-protected-resource` URL | aligned |
| `rfc9068` JWT access tokens | `typ`=`at+jwt`, required claims, audience, not expired | aligned (tokens we *accept*) |
| `rfc7636` PKCE | `S256` challenge = base64url(sha256(verifier)) without padding | aligned |
| `backends` | every driver exposes the full backend contract | aligned |
| `no-passthrough` | an HTTP header injection never carries the client token | aligned |
| `rfc9449` DPoP | — | **not supported** (v0.3.0); the suite is skipped, never implied |

A failing suite is a release blocker. Unsupported suites report `not-supported` and never `pass`.

## 2. Evidence scanner (SC-43)

`scan_evidence(store)` walks every ledger row (canonical JSON), the export render, and redaction receipts
for credential shapes. Any hit fails with the row `seq` and the masked class — never the value. A seeded
leak must fail; a clean store passes.

## 3. Invariants I1–I10

Each invariant is a named, executable probe over a live broker context; the test suite also runs a
**negative fixture** that breaks the context and asserts the probe goes red. An invariant without a
red-when-violated test is not claimed.

## 4. Attack packs (release-blocking)

`context-dump`, `tamper`, `widening`, `spoof-replay`. Each pack returns pass/fail with a detail; the test
proves a deliberately broken gate turns the pack **red**.

## 5. Supply-chain floor (E15)

Checked in-repo: runtime dependencies empty (stdlib only), dev dependencies bounded, `security.txt` present,
CI runs lint/type/test/coverage, and a CycloneDX SBOM can be generated from installed metadata. Signature
and SLSA attestation require release credentials and are **not claimed** here — M15 owns them.

## 6. Offline / air-gap (SC-39)

The core resolve → use → revoke path runs with sockets disabled; an unsupported cloud backend warns and
refuses (unknown driver), never silently degrades.

## 7. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 11.1 | `tests/test_conformance_kit.py` | every suite passes; unsupported is skipped; a broken check turns it red |
| 11.2 | `tests/test_evidence_scan.py` | clean store passes; a seeded leak fails with the row; receipts reported |
| 11.3 | `tests/test_invariants.py` | I1–I10 pass, each has a negative fixture that fails |
| 11.4 | `tests/test_attack_packs.py` | four packs pass; a broken gate turns a pack red |
| 11.5 | `tests/test_supply_chain.py` | deps/security.txt/CI/SBOM checks pass |
| 11.6 | `tests/test_offline.py` | resolve/use/revoke with sockets disabled; cloud backend refuses |

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `11.CR`.
