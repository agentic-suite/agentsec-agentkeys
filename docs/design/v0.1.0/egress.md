# Egress design — one injection interface, three drivers (M4)

**Status:** design of record for M4 · **Issue:** #54 (`4.D0`) · **Written before implementation.**
**Sources:** [PRD 02 §4](../../prd/02-architecture.md), [PRD 16 §3](../../prd/16-adapters-and-integration.md),
[PRD 18 §3-§4](../../prd/18-issuance-integrity.md), [contracts design](contracts.md).

**BLUF:** A minted issuance reaches a target through exactly one `Injector`: the child environment, an HTTP
header, or an RFC 8693 token exchange. Four rules are normative for every driver — **cannot widen**, **never
forwards the client's token**, **enforces the audience at the injector**, and **forgets**. A rejected
injection is a typed denial plus an `exchange-rejected` event, never a silent pass.

---

## 1. The contract

```python
class Injector(Protocol):
    kind: str                                   # "env" | "header" | "exchange"
    def target_audience(self) -> str: ...
    def apply(self, resolved: ResolvedIssuance, *, request: InjectionRequest) -> Injection: ...
    def forget(self) -> None: ...               # nothing about the resolution stays observable

@dataclass(frozen=True)
class InjectionRequest:                          # what the caller is about to do
    audience: str
    tool: str
    client_token: str | None = None               # whatever the harness tried to send
    client_headers: Mapping[str, str] = {}        # for header targets

@dataclass(frozen=True)
class Injection:
    kind: str
    audience: str
    secret: SecretValue                           # the broker-minted credential, applied at egress
    env: Mapping[str, str] | None = None          # env driver
    headers: Mapping[str, str] | None = None      # header driver
    token: SecretValue | None = None              # exchange driver
    actor: str | None = None                      # `act` identity for the exchanged token
    receipts: tuple[RedactionDraft, ...] = ()     # masked fields (the injected value is never one)
    overwrote_client_credential: bool = False
```

Normative rules:

1. **The binding is the ceiling (E7).** `target_audience()` must equal the issuance's audience; a request
   asking for another audience, another tool, or a wider scope raises `WideningRefused`.
2. **No passthrough (E14).** `request.client_token` is recorded as *stripped* and never appears in the
   injected material, the exchanged request, or the receipts. A header driver removes any client-supplied
   credential header before setting its own.
3. **Audience enforcement at the injector.** The driver re-checks the audience itself — it does not ask the
   downstream to check. A mismatch is `AudienceMismatch`, mapped to `exchange-rejected`.
4. **Forget.** `forget()` clears anything the driver held; a test asserts a second `apply` without a new
   resolution cannot reuse the previous secret.

Denials: `InjectionDenied(reason)` with reasons `widening-refused`, `audience-mismatch`, `expired`,
`token-unavailable`,
`already-consumed`, `passthrough-stripped`, `injector-unavailable`. Each denial produces a
`rejection_event()` (name `exchange-rejected`, severity `warn`) so the attempt is evidence, not a mystery.

## 2. Drivers

| Driver | Kind | Applies | Notes |
|---|---|---|---|
| env-virtualization | `env` | a `Mapping[str, str]` for a child process environment | The parent shell/dev environment never holds it; the child receives it at its own egress. The reference is never in the child env — only the scoped token (M5 uses this). |
| HTTP header | `header` | request headers | Sets `<header>: <scheme> <token>`, removing any client-supplied `authorization`-family header first; records `overwrote_client_credential`. The header is never placed in anything the agent can read back. |
| RFC 8693 exchange | `exchange` | a narrow downstream token | POSTs a token-exchange request with `subject_token` = the backend secret, `audience` = the target, `scope` = the tool, and `actor_token` for `act` semantics. The client token is never the subject. |

The exchange driver takes an injectable `exchange_fn` (so tests never hit a network) and always requests the
narrowest form: one audience, one tool scope, one use.

## 3. Session binding (D-17)

`SessionBinder` binds **one agent identity per session**: the first `bind(session_id, agent_id)` wins; a
second *different* agent is refused with `SessionConflict` and an event. Bindings die with the session
(revocation epoch > 0 → refuse), and there is no ambient inheritance: a new session starts unbound.

## 4. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 4.1 | `tests/test_inject_contract.py` | the four rules; `forget()` clears; denial → `exchange-rejected` event; a widening request raises |
| 4.2 | `tests/test_inject_env.py` | env driver returns only the scoped value; the parent environment and the returned mapping carry no reference and no client token |
| 4.3 | `tests/test_inject_header.py` | sets the header; strips a client-supplied credential; audience fixed; agent never sees the header in the response object |
| 4.4 | `tests/test_inject_exchange.py` | the exchange request has `audience`=target, `scope`=tool, `subject_token`=backend secret, `act`; the client token is absent |
| 4.5 | `tests/test_binding_audience.py` | SC-08-SC-11 + SC-42: wrong/absent audience, cross-tool, stale, forwarded → deny + event |
| 4.6 | `tests/test_binding_session.py` | one agent per session; second agent refused; revoked session refuses; new session unbound |

## 5. Honest limits

- Delivery over a real network is out of scope for tests (the exchange driver uses an injected function);
  the M14 field test exercises a live target.
- Tool *scope narrowing* is expressed as the requested scope string; enforcement that a token cannot exceed
  the tool's own authorization is the downstream's job and is documented, not claimed.
- stdio delivery (the flagship) is M5; M4 proves the engine and the three drivers.

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `4.CR`.