# Egress reference — the three injection drivers (v0.1.0)

**Status:** implemented in M4 · **Owner modules:** `src/agentkeys/egress/`, `src/agentkeys/core/sessions.py` ·
**Design:** [egress design](../design/v0.1.0/egress.md) · **Issue:** WBS 4.D.

**BLUF:** One `Injector` interface, three drivers, four rules that no driver may break: **cannot widen**,
**never forwards the client's token**, **enforces the audience at the injector**, **forgets**.

## The contract

`Injector.kind` · `target_audience()` · `apply(resolved, request=InjectionRequest, now=)` → `Injection` ·
`forget()`. `InjectionRequest(audience, tool, client_token?, client_headers?, scope?)`; `Injection(kind,
audience, secret: SecretValue, env?, headers?, token?, actor?, receipts?, overwrote_client_credential)`.

`BaseInjector.apply` performs the shared enforcement before delegating to the driver's `_deliver`:

1. `request.audience` and the injector's own audience must equal `issuance.binding.audience` → else
   `AudienceMismatch`.
2. `request.tool` must equal the bound tool, and a supplied `scope` may not exceed it → else
   `WideningRefused`.
3. An issuance whose `expires_at` has passed → `InjectionDenied("expired")`.
4. No transient token in this process → `InjectionDenied("token-unavailable")`.
5. A client token that would appear in the injected material → `InjectionDenied("passthrough-stripped")`.

## Drivers

| Driver | Kind | Applied material | Notes |
|---|---|---|---|
| `EnvInjector(audience, variable=AGENTKEYS_SCOPED_TOKEN)` | `env` | `{variable: token}` | For a child process's own egress; the parent environment is untouched and the reference never appears. |
| `HeaderInjector(audience, header="Authorization", scheme="Bearer")` | `header` | request headers | Removes client-supplied `authorization`/`proxy-authorization`/`x-api-key`/`api-key` headers, then sets its own (`overwrote_client_credential=True`). |
| `ExchangeInjector(audience, exchange_fn, actor_token=…, actor=…)` | `exchange` | a narrow downstream token | RFC 8693 token exchange: `grant_type`, `subject_token` = the **broker's** single-use token, `audience` = target, `scope` = tool, `actor_token`. `exchange_fn` is injected (tests never touch a network). |

## Denials and evidence

| Denial reason | Meaning |
|---|---|
| `audience-mismatch` | the request or the injector targets another audience |
| `widening-refused` | another tool or a wider scope was requested |
| `expired` | the issuance's TTL has elapsed |
| `token-unavailable` | the transient token is not available in this process |
| `passthrough-stripped` | a client token would have reached the output |
| `injector-unavailable` | the driver could not deliver (e.g. the exchange returned nothing) |

Refusals are recorded with `RejectionLog.record(...)`/`record_denial(...)`, which produce
`exchange-rejected` events (severity `warn`) — a refused replay is evidence, never silence.

## Session binding (D-17)

`SessionBinder(store)` enforces **one agent identity per session**: `bind(session_id, agent_id)` returns the
session or raises `SessionConflict` (`unknown-session`, `session-revoked`, or another agent's session).
`agent_for(session_id)` never invents an identity — a new session starts unbound.

## Honest limits

- Tool-scope narrowing is expressed as the requested scope; that a downstream token cannot exceed the tool's
  own authorization is the downstream's policy, and is not claimed here.
- Tests inject a fake exchange function; a live exchange is exercised in the M14 field test.
- stdio delivery is M5; M4 proves the engine, the three drivers, enforcement, and session binding.
