# Appendix — stdio credential virtualization for MCP ext-auth (staged, v0.1.0)

**Status:** staged for the MCP external-auth contribution (M11) · **Issue:** WBS 5.5 (fixtures + appendix).

This appendix records the shape agentkeys proposes for **stdio** MCP credential handling, so the M11
contribution has a concrete, tested artifact to point at rather than a claim.

## The problem this addresses

MCP defines HTTP authorization; a **stdio** server is a child process with no network boundary. The common
practice — put the token in the server's `env` or config — means the token is readable by the server, by any
co-located agent code, and by anything that can dump the process environment.

## The proposed pattern

1. **References, not values.** Configuration carries `akref:<backend>/<path>` placeholders.
2. **Substitution at spawn, scoped per call.** A broker resolves the placeholder into a token bound to
   `(audience, tool, session)`, single-use, short-lived.
3. **No passthrough.** A client-supplied credential is stripped; the server can only ever receive a
   broker-minted credential.
4. **Transparency.** The broker is a byte-transparent stdio proxy; it never rewrites the JSON-RPC stream and
   logs only to stderr.

## Fixtures staged for the contribution

| Fixture | Where |
|---|---|
| A stock JSON-RPC child launched under the broker, authenticating with a substituted token | `tests/test_stdio_virtualization.py` |
| Placeholder → scoped-token substitution with receipts | `tests/test_stdio_virtualization.py` |
| No-passthrough for a client-supplied credential | `tests/test_stdio_no_token_passthrough.py` |
| Transparent proxy with a frame cap and stderr-only logging | `tests/test_stdio_proxy.py` |
| The `agentkeys run --server` CLI path, including the stripped-literal case | `tests/test_stdio_cli_run.py` |

## Open questions to raise upstream

- Whether MCP should normatively define a placeholder grammar for stdio config, or leave it to the broker.
- How a server should *declare* that its credential is broker-supplied (an ext-auth capability flag).
- Whether the proxy must be the process parent for the no-passthrough guarantee to hold.
