# WBS v0.1.0 — Part 3: Egress & the stdio Flagship (M4–M5)

**BLUF:** **M4 builds the egress-injection engine** — one interface, three drivers (**env-virtualization**,
**HTTP header**, **RFC 8693 exchange**) — with the binding enforced *at the injector* so no driver can widen
an audience and no client token is ever forwarded ([E7](../../prd/05-features.md),
[E14](../../prd/05-features.md)). **M5 ships the flagship** nobody else has: **stdio MCP credential
virtualization** ([R8](../../prd/05-features.md), coverage-map row #8) — a local server launched under the
broker whose config/env hold references while scoped tokens are supplied at call time, with the honest
process-boundary limit documented.

> **Standard exit criteria + closure apply to every milestone** — see the
> [index](wbs-v0.1.0-index.md): **design docs first (`.D0`)**, then implement, then close with
> **`.T` tests · `.C` coverage ≥95% · `.L` ruff + `mypy --strict` · `.CR` review · `.D` docs + traceability ·
> `.CI` commit · `.W` WBS checkpoint**.

---

## Milestone M4 — Egress-injection engine: env / header / RFC 8693 (R2, R3, E7, E14)

**Goal:** a minted issuance can reach a real target — as a virtualized child-process environment, an injected
HTTP header, or an RFC 8693 exchange — with the audience enforced at egress and token passthrough forbidden.
This is where [CUJ-5](../../prd/04-users-and-cujs.md) (bindings) and [CUJ-12](../../prd/04-users-and-cujs.md)
(one broker, many harnesses) become real.

**CUJ:** [CUJ-5](../../prd/04-users-and-cujs.md), [CUJ-12](../../prd/04-users-and-cujs.md) ·
**Requirements:** [R2](../../prd/05-features.md), [R3](../../prd/05-features.md),
[E7](../../prd/05-features.md), [E14](../../prd/05-features.md), [E13](../../prd/05-features.md),
[PRD 02 §4](../../prd/02-architecture.md), [PRD 16 §3](../../prd/16-adapters-and-integration.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 4.D0 | **Design docs first** | Injection interface + the three drivers; the shared rules (no widening, no passthrough, forget); audience enforcement point | docs | reviewed before code | #54 | — | — |
| 4.1 | Injection interface + shared rules | One interface; binding is the **ceiling**; injector enforces audience even if the downstream won't; nothing observable to the agent | interface module | conformance fixtures per driver; a widening attempt is refused | #55 | [CUJ-5](../../prd/04-users-and-cujs.md) | [E7](../../prd/05-features.md), [R3](../../prd/05-features.md) |
| 4.2 | Env-virtualization driver | Apply the scoped value into a child process's environment at its egress; the parent shell never holds it | driver | child authenticates; parent env + transcript hold only the reference | #56 | [CUJ-12](../../prd/04-users-and-cujs.md) | [R2](../../prd/05-features.md) |
| 4.3 | HTTP header driver | Attach `Authorization: Bearer <bound-token>` to the outbound request, overwriting any client-supplied credential | driver | 2xx authenticated; header never visible to the agent; audience fixed | #57 | [CUJ-5](../../prd/04-users-and-cujs.md) | [R2](../../prd/05-features.md) |
| 4.4 | RFC 8693 exchange driver | Exchange to obtain a narrow, audience-bound token with `act` semantics; **no passthrough** | driver | exchange succeeds; token audience == target; scope == tool op | #58 | [CUJ-5](../../prd/04-users-and-cujs.md) | [R2](../../prd/05-features.md), [E13](../../prd/05-features.md) |
| 4.5 | Audience enforcement + replay rejection | Refuse to inject on wrong/absent audience; log `exchange-rejected`; cross-bound/stale/forwarded attempts fail | enforcement module | SC-08–SC-11 + SC-42 all fail closed and are logged | #59 | [CUJ-5](../../prd/04-users-and-cujs.md) | [E14](../../prd/05-features.md), [R3](../../prd/05-features.md) |
| 4.6 | Session binding model | One agent identity per session; binding dies with the session (D-17); no ambient inheritance | session module | a second agent in one session is rejected + logged | #60 | — | [R3](../../prd/05-features.md) |
| 4.T | Tests | Driver conformance + enforcement + session | tests | coverage ≥95% | #61 | — | — |
| 4.C | Coverage gate | ≥95% on engine modules | coverage report | ≥95% | #62 | — | — |
| 4.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #63 | — | — |
| 4.CR | Code review | Findings resolved | review log | no open findings | #64 | — | — |
| 4.D | Docs | [PRD 02 §4](../../prd/02-architecture.md); [PRD 16 §3](../../prd/16-adapters-and-integration.md); [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #65 | — | — |
| 4.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 4.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] All three drivers pass conformance; the audience is enforced at the injector; no passthrough exists
- [ ] Binding replay (audience/tool/session/stale) fails and is logged ([SC-08–SC-11](../../prd/17-scenarios.md))

**Planned (opens at `4.D0`).** Design: [`docs/design/v0.1.0/egress.md`](../../design/v0.1.0/) · Scenarios:
[SC-02–SC-04](../../prd/17-scenarios.md), [SC-08–SC-11](../../prd/17-scenarios.md), [SC-42](../../prd/17-scenarios.md) ·
Tests: `tests/test_inject_env.py`, `tests/test_inject_header.py`, `tests/test_inject_exchange.py`,
`tests/test_binding_audience.py`, `tests/test_binding_tool.py`, `tests/test_binding_session.py`.

---

## Milestone M5 — stdio MCP credential virtualization (R8, E7, E14)

**Goal:** the flagship — a local **stdio MCP server** (or CLI) launched **under the broker** so its config
and environment hold only references/placeholders, and the credential is supplied by the broker at the
child's egress. The server authenticates; the secret is never in its config, env, logs, or the agent's
transcript. The honest co-located-runtime limit is documented, not hidden
([PRD 06 §4](../../prd/06-security-baseline.md)).

**CUJ:** [CUJ-4](../../prd/04-users-and-cujs.md) · **Requirements:** [R8](../../prd/05-features.md),
[E7](../../prd/05-features.md), [E14](../../prd/05-features.md), [PRD 06 §4](../../prd/06-security-baseline.md),
[PRD 02 §5](../../prd/02-architecture.md).

**Work items**

| # | Task | Description | Deliverable | Acceptance | Issue | CUJ | Req |
|---|---|---|---|---|---|---|---|
| 5.D0 | **Design docs first** | Wrapper/sidecar design; the process boundary; stdio proxy rules; the honest co-located-runtime limit | docs | reviewed before code | #66 | — | — |
| 5.1 | Launch wrapper `agentkeys run --server` | Broker launches the child under a protected boundary; child env holds references/placeholders | CLI + wrapper | server starts under the broker; config/env contain no real secret | #67 | [CUJ-4](../../prd/04-users-and-cujs.md) | [R8](../../prd/05-features.md) |
| 5.2 | stdio JSON-RPC proxy | Proxy stdio frames untouched; **logs to stderr only** (never stdout); size/complexity caps | proxy module | frames pass through; stdout stays clean; oversized frame rejected | #68 | [CUJ-4](../../prd/04-users-and-cujs.md) | [R8](../../prd/05-features.md) |
| 5.3 | Credential substitution at child egress | Resolve the reference and inject a scoped token at the child's egress (env/header/exchange per target) | substitution module | upstream call authenticates; a scan of config/env/transcript finds 0 secrets | #69 | [CUJ-4](../../prd/04-users-and-cujs.md) | [R8](../../prd/05-features.md) |
| 5.4 | No-passthrough for stdio | A client-supplied token is never forwarded; the upstream receives a broker-minted scoped credential | enforcement | upstream sees a broker token; client token never forwarded | #70 | [CUJ-4](../../prd/04-users-and-cujs.md) | [E14](../../prd/05-features.md) |
| 5.5 | Reference pattern docs + ext-auth prep | The reference/placeholder pattern for server authors; fixtures + threat appendix staged for the MCP ext-auth contribution | docs | pattern documented; fixtures + appendix exist for [PRD 20 §3](../../prd/20-standards-and-claims.md) | #71 | — | [R8](../../prd/05-features.md) |
| 5.T | Tests | Wrapper, proxy, substitution, no-passthrough | tests | coverage ≥95% | #72 | — | — |
| 5.C | Coverage gate | ≥95% on stdio modules | coverage report | ≥95% | #73 | — | — |
| 5.L | Lint & type gate | `ruff` zero; `mypy --strict` clean | CI | zero violations | #74 | — | — |
| 5.CR | Code review | Findings resolved | review log | no open findings | #75 | — | — |
| 5.D | Docs | [PRD 16 §3](../../prd/16-adapters-and-integration.md) stdio recipe; boundary doc; [PRD 12](../../prd/12-traceability.md) rows | docs | docs updated + linked | #76 | — | — |
| 5.CI | Commit & push | Feature branch | git | pushed | — | — | — |
| 5.W | Update WBS | Checkpoint in the index Progress | WBS | recorded | — | — | — |

**Exit criteria**

- [ ] Design docs first · tests · coverage ≥95% · lint clean · docs · committed+pushed
- [ ] A stock stdio server authenticates with no secret in config/env/transcript ([SC-12](../../prd/17-scenarios.md))
- [ ] No token passthrough for stdio ([SC-13](../../prd/17-scenarios.md)); the boundary limit is documented

**Planned (opens at `5.D0`).** Design: [`docs/design/v0.1.0/stdio.md`](../../design/v0.1.0/) · Scenarios:
[SC-12/SC-13](../../prd/17-scenarios.md) · Tests: `tests/test_stdio_virtualization.py`,
`tests/test_stdio_no_token_passthrough.py`.

---

Part 3 green ⇒ credentials flow at egress and the flagship works; proceed to
[Part 4 (M6–M7)](wbs-v0.1.0-part4-revoke-ledger.md).
