# stdio virtualization design — the flagship (M5)

**Status:** design of record for M5 · **Issue:** #66 (`5.D0`) · **Written before implementation.**
**Sources:** [PRD 02 §5](../../prd/02-architecture.md), [PRD 06 §4](../../prd/06-security-baseline.md),
[PRD 16 §3](../../prd/16-adapters-and-integration.md), [egress design](egress.md).

**BLUF:** A stdio MCP server (or CLI) is launched **under the broker** with an environment that holds
**references, not secrets**; the broker resolves each reference and substitutes a short-lived, scoped token at
the child's egress. The server authenticates, and a scan of its config, environment, and the agent's
transcript finds **zero credentials**. The honest limit — a co-located runtime can read what that runtime can
read — is documented, not hidden.

---

## 1. Process boundary and data flow

```text
harness ──stdio JSON-RPC──▶ agentkeys run --server <ref> -- <child argv>
                                  │            (1) build child env: references → placeholders
                                  │            (2) strip any client credential from the env
                                  │            (3) spawn child with the virtualized env
                                  │            (4) pump frames verbatim, both directions
                                  └── resolve(placeholder) ──▶ scoped token, delivered at child egress
```

Rules:

1. **The child's config and environment never hold a real secret.** Values in the child env are either
   non-secret configuration or **placeholder references** (`akref:<backend>/<path>`).
2. **No passthrough (E14).** Any client-supplied credential variable/header is removed before the child
   starts; the child can only receive a broker-minted, broker-scoped token.
3. **The proxy is transparent and quiet.** Frames pass byte-for-byte; the proxy logs **only to stderr** and
   never writes to the JSON-RPC stream; it applies a frame size cap and refuses an oversized frame.
4. **Scoped substitution.** A placeholder resolves to a token bound to `(reference, audience, tool, session)`
   through `ResolutionCore`, so the child receives the narrowest credential.

## 2. Modules

| File | Contents |
|---|---|
| `src/agentkeys/stdio/substitute.py` | `Placeholder` parsing, `Substitution` (virtualized env + receipts), `strip_client_credentials`, `assert_no_passthrough` |
| `src/agentkeys/stdio/proxy.py` | `FrameCheck`, `forward_frame`, `StdioProxy` (spawn + pump, stderr-only logging, size cap) |
| `src/agentkeys/stdio/wrapper.py` | `build_child_env(...)`, `launch(...)` — the `agentkeys run --server` path |
| `src/agentkeys/cli.py` | `run` command wiring (`--server`, child argv after `--`) |

## 3. Denials and evidence

| Failure | Result |
|---|---|
| unknown/absent placeholder | `SubstitutionError` naming the placeholder (never a value) |
| placeholder for a reference the session may not use | `SubstitutionError` (binding refusal) |
| frame above `max_frame_bytes` | `FrameTooLarge` — logged to stderr, frame not forwarded |
| child exits | the child's exit code is returned, unchanged |
| client credential present in the env | stripped, counted, and reported as `passthrough_stripped` |

## 4. The honest co-located-runtime limit (PRD 06 §4)

The broker moves the credential **across a process boundary**: the child receives a scoped token at use time
rather than a durable secret in its environment. If the child shares a runtime where arbitrary agent code can
read the broker's memory or the token it was handed, that runtime can still read what it was handed — **the
token, scoped to one audience/tool/session and short-lived**, not the underlying long-lived credential.

- **Documented property, not a footnote:** the limitation is written here, in
  [`stdio-virtualization.md`](../../reference/stdio-virtualization.md), and will be recorded in the M14 field
  test report.
- **Blast radius is bounded** by the scoped, single-use issuance and by `revoke` (M6), which kills the next
  resolve ≤1s.
- **We never claim a guarantee we cannot hold:** where the boundary cannot be established, agentkeys says so
  and records the attempt.

## 5. Test plan

| Ticket | Test file | Key assertions |
|---|---|---|
| 5.1 | `tests/test_stdio_virtualization.py` | child env holds only placeholders; a stock server starts and authenticates with a substituted scoped token; a scan of env/config/transcript finds 0 secrets |
| 5.2 | `tests/test_stdio_proxy.py` | frames pass byte-for-byte; a log line goes to stderr and never to the JSON-RPC stream; an oversized frame is refused |
| 5.3 | `tests/test_stdio_virtualization.py` | substitution resolves through the reference/binding; unknown placeholders refuse; receipts are emitted |
| 5.4 | `tests/test_stdio_no_token_passthrough.py` | a client token in the env is stripped; the child never receives it; the upstream receives a broker token |
| 5.5 | docs + fixtures | the reference/placeholder pattern is documented with fixtures and the ext-auth appendix |

## 6. Review

Settled here: (1) the child env carries references/placeholders only, and client credentials are stripped
before spawn; (2) the proxy is transparent and stderr-only, with a frame cap; (3) substitution goes through
the same `ResolutionCore` as every other path (no parallel minting); (4) the co-located limit is documented
as a first-class property. Deferred: real harness recipes and the MCP ext-auth contribution (M10/M11), the
live field test (M14).

Findings land in [`codereview-log.md`](../../wbs/v0.1.0/codereview-log.md) at `5.CR`.
