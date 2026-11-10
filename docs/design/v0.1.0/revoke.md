# Revocation design — one CAS, a proven kill, and time that cannot be gamed (M6)

**Status:** design of record for M6 · **Issue:** #77 (`6.D0`) · **Written before implementation.**
**Sources:** [PRD 18 §7](../../prd/18-issuance-integrity.md), [PRD 15 §5–§6](../../prd/15-data-model.md),
[PRD 05 R4/E6](../../prd/05-features.md), [PRD 17 §8/§15](../../prd/17-scenarios.md),
[store design](store.md), [contracts design](contracts.md).

**BLUF:** Revocation is a **compare-and-set on `sessions.revoke_epoch`**, not a walk of issued tokens.
That single atomic write is why the kill is O(1), why a scoped kill never over-kills, and why the ≤1s
number is honest. A killed session refuses the next resolution *and* refuses a replay of the token minted
before the kill. Time correctness is the second half: absolute instants plus a non-decreasing clock view,
so a backwards jump cannot extend a TTL and a forwards jump cannot resurrect one.

---

## 1. The kill model

| Scope | Target | Store operation | Over-kill? |
|---|---|---|---|
| `session` | one `session_id` | `cas_revoke(scope="session", target_id=<session>)` | No — one epoch |
| `agent` | one `agent_id` | `cas_revoke(scope="agent", target_id=<each session>)` | No — only that agent's sessions |
| `all` | the whole store | `cas_revoke(scope="all", target_id=<each session>)` | Explicit by flag; never implied |

Rules:

1. **Unconditional.** Revocation is never gated on policy (D-07). The broker does not ask permission.
2. **CAS, not read-modify-write.** The store increments `revoke_epoch` only when it matches the epoch it
   read. A concurrent revoke loses cleanly and returns `winner=False`.
3. **Unknown target is loud.** A scoped revoke of a nonexistent session/agent is an error (`DENIED`,
   exit `2`), never a silent no-op (SC-27). `--all` with an empty store is also a loud error.
4. **Attribution.** Each `revoked` event carries `session_id`, `agent_id`, the operator principal, the
   reason, and the monotonic measurement against the ≤1s budget (SC-28).

## 2. What "dead" means, and how replay proves it

A killed session is dead on **every** path that can hand out or accept a credential:

- `ResolutionCore.resolve` reads the session first and refuses when `revoke_epoch > 0`.
- `ResolutionCore.use` re-reads the session and returns `rejected` when the epoch is set — a token minted
  before the kill stops authenticating at its next use.
- `agentkeys replay --last` re-runs the resolution of the last pre-revoke issuance and exits `4`
  (`REVOKE_VERIFIED`) **only** when it is refused. A green `revoked` event without a refused replay is not
  evidence (PRD 17 §15).

The replay command never needs the plaintext token (by design it was never stored): it replays the
*binding* (`reference`, `audience`, `tool`, `session`) and asserts the epoch refuses it.

## 3. Kill-time harness (SC-24)

`agentkeys.bench.killtime` measures, per iteration:

1. `t0 = monotonic_ns()` immediately before the revoke call;
2. revoke the session;
3. replay the pre-revoke resolution until it is refused;
4. `t1 = monotonic_ns()` at the refusal; `kill_time = t1 - t0`.

It reports **p50, p95, max** over `N ≥ 100` iterations and emits JSON. PASS requires **p95 ≤ 1s and
max ≤ 1s**; a single max over budget is a FAIL. The test runs the bench in CI with N=100 on the in-memory
driver and the SQLite driver's semantics (the wall-clock budget is the same store write).

## 4. Time correctness (E6)

`TimeGuard` is the only clock the revoke/expiry paths use:

- **Absolute instants** — `expires_at = issued_at + ttl` is persisted; expiry is `now >= expires_at`.
- **Non-decreasing wall view** — the guard remembers the last wall second it observed. A backwards jump
  within `clock.skew_tolerance` is floored (it cannot extend a TTL). A jump beyond tolerance raises
  `ClockSkewError`; the caller **denies** rather than guessing.
- **Forwards jump** — the next read expires everything due; it never resurrects a consumed/expired row.
- **Expiry fires once** — `ExpirySweeper` calls `store.expire_due(now, event)` which CASes
  `status='live' → status='expired'` and returns only the rows that transitioned, so one event per
  issuance, ever.

## 5. Surfaces

```python
Revoker(store, clock).revoke(scope, target=None, *, reason, requested_by) -> RevokeOutcome
ResolutionCore.use(...)            # now consults the session epoch (revoked -> "rejected")
agentkeys revoke [TARGET] [--agent ID | --session ID | --all] [--reason R] [--json]
agentkeys replay --last [--json]   # exit 4 only when the pre-revoke attempt is refused
TimeGuard(clock=..., skew_tolerance=...).now() / .is_expired(expires_at)
ExpirySweeper(store, guard).sweep() -> tuple[LedgerEvent, ...]
```

Store additions (additive, E11): `list_sessions()`, `expire_due(now, event)`.

## 6. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 6.1 | `tests/test_revoke_scope.py` | session CAS kills one session; replay/resolve refused; `revoked` event attribution |
| 6.2 | `tests/test_revoke_killtime.py` | N=100; p95 and max ≤1s; a refused replay is the proof |
| 6.3 | `tests/test_revoke_cli.py` | `replay --last` exits 4 only after a refused resolution; no success reports 4 |
| 6.4 | `tests/test_revoke_scope.py` | agent/all scopes; scoped kills do not over-kill; unknown target is loud |
| 6.5 | `tests/test_time_correctness.py` | backwards jump cannot extend; forwards expires; expiry fires exactly once |
| 6.6 | `tests/test_revoke_scope.py` | `revoked` carries scope/target/principal/effective_at |

## 7. Honest limits

- The kill-time number is measured on the broker's store write plus the replay refusal on the same host;
  network round-trips to a downstream are the downstream's latency and are not claimed.
- A credential already *in flight* completes its current hop; the **next** hop fails (PRD 18 §7, SC-26).
  The test models the next-hop refusal, not an ability to retract bytes already sent.
- `agent` scope is a fan-out of session CAS writes (one per session). It is still unconditional and
  bounded by the agent's session count; a future server mode may make it a single fleet CAS (R11).

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `6.CR`.
