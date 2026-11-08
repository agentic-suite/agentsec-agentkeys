# Glossary

**BLUF:** The controlled vocabulary of agentkeys — every security product accumulates jargon; the
discipline is making each term mean **exactly one thing**. Where a term has a product-claim meaning
(*brokered*, *revocable ≤1s*), the strict definition lives in the
[claims vocabulary](../prd/20-standards-and-claims.md) (§6a); this page is the plain-language index.

| Term | Definition | Where |
|---|---|---|
| **Reference** (`akref:`) | The opaque handle an agent holds instead of a secret — names a backend slot, carries no secret bytes, safe to log and leak by design | R1, D-04 |
| **Backend** | The store that actually holds the secret: OS keychain, credential file (v0.1.0); 1Password/Vault/K8s/cloud SM (R10). We never store secrets ourselves | R5, D-01 |
| **Binding** | The triple that constrains every issuance: **audience** (one server, RFC 8707) × **tool** (one operation) × **session** (one conversation). The ceiling no injector may widen | R3, E7 |
| **Issuance** | One mint of a short-lived credential against a reference+binding — single-use, hashed at rest, idempotent per window | R3, E3 |
| **Execution credential** | The short-lived token that actually crosses to the target — the only place plaintext exists, transiently, at egress | [PRD 18 §2](../prd/18-issuance-integrity.md) |
| **Egress injection** | Resolving at moment-of-use and applying the credential where the target reads it: child-process env, HTTP header, or RFC 8693 exchange — never into agent context | R2, E7 |
| **stdio virtualization** | Launching a local stdio MCP server under the broker so its config/env hold references while the broker supplies scoped tokens at call time (coverage row #8 — nobody else) | R8 |
| **Session** | One agent's conversation-scoped context of authority; bindings die with it; exactly one agent per session (D-17) | R3, D-17 |
| **Revoke epoch** | The monotonic counter a revoke CAS-increments; every check consults it — why the kill is O(1) and ≤1s is honest | R4, [PRD 18 §7](../prd/18-issuance-integrity.md) |
| **Kill-time** | t0 (revoke dispatches) → t1 (**replay of the pre-revoke credential fails**). Never the command's return time; the replay is the proof | R4, SC-24 |
| **Step-up** | The gate that makes a higher-class (prod) mint impossible without an approving human decision, via agentpolicy; timeout = deny | R9 |
| **Fail-closed** | Every failure (locked backend, corrupt store, offline sink, ambiguous config) resolves to **deny or pending** — never to a static secret or env fallback | E4, I2 |
| **Never-in-context** | The permanent invariant: a full dump of the agent's world finds **zero usable** credentials — CI-gated, not a demo | R1, I1 |
| **Context-dump** | The simulated full compromise (transcript + env + args + config + logs) the attack pack scans; **usable** = matches a secret shape **and** authenticates or is a raw backend secret | SC-40, [PRD 21 §3](../prd/21-evidence-register-and-method.md) |
| **Secret-evasion** | An attempt to read a raw credential outside the broker (`.env`, cloud cred files, keychain) — a high-severity event; blocked in enforce mode where an enforcer composes | R7 |
| **Canary reference** *(R19)* | A broker-registered decoy that looks identical to a real reference; any use attempt = attacker-in-context signal; pages immediately | R19, SC-53 |
| **Passthrough** | Forwarding a client's token upstream — the MCP-named anti-pattern we never do; we mint a broker-scoped token instead | E14 |
| **Monitor-safe vs enforce** | Detection-and-log vs block-where-an-enforcer-composes; the honest rule is we name any gap instead of claiming a block | R7 |
| **Ledger** | The append-only, hash-chained local record of the credential lifecycle; tamper-evident (`verify-log`), export secret-free | R6, E12 |
| **Recipe** | The per-harness config+docs that point a harness at the one broker — never a code fork; gated by that harness's attack pack | [PRD 16](../prd/16-adapters-and-integration.md) |
| **Lower-layer coverage** | Coverage of a harness with a closed hook surface via the process/network layer — labeled honestly, never as a first-class recipe | [PRD 19 §7](../prd/19-harness-compatibility.md) |
| **Posture** | The residual-risk report: env-resident secrets, unbrokered servers, TTL drift, revoke counts | R18 |
| **Evidence labels** | *documented → conformance → field-tested → verified* — no claim may wear a higher label than its proof | [PRD 20 §6](../prd/20-standards-and-claims.md) |

## Related

- The contracts these terms live in: [PRD 15 — Data model](../prd/15-data-model.md)
- The decisions that froze them: [PRD 11 — Decisions](../prd/11-decisions.md)
- The commands that operate them: [CLI reference](cli.md)
