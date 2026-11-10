# Contributing to agentkeys

Thanks for helping. This repo is built to the published plan of record, not to improvisation:
the **[PRD set 00–23 + Appendix A](docs/prd/README.md)** defines the requirement set (v0.1.0 is the P0
features R1–R9 + R17 and E1–E15), and the
**[v0.1.0 WBS](docs/wbs/v0.1.0/)** defines the milestone order and exit gates.

## Workflow (one ticket at a time)

1. Pick the next open work item from the WBS milestone (its GitHub issue).
2. **Test-first:** write the failing test for that item only, and watch it fail (RED).
3. Implement the smallest change that makes it pass (GREEN).
4. Run **only** that test. Do not run the full suite between tickets.
5. Commit and push on a feature branch. The full gate (suite, coverage, `ruff`,
   `mypy --strict`) runs **once at milestone end**, not per ticket.

Design docs are written before code for every milestone; they live in
[`docs/design/v0.1.0/`](docs/design/v0.1.0/).

## Local commands

```sh
make setup      # .venv + editable install + dev tools
make lint       # ruff
make typecheck  # mypy --strict
make test       # pytest
make cov        # pytest with the coverage gate
make gate       # the milestone gate (run once, at milestone end)
```

The runtime is stdlib-only by design. Do not add a runtime dependency without an explicit
decision recorded in the design docs — "standalone" is a product property, not an accident.

## Commits

Every commit must be **DCO signed off**:

```sh
git commit -s -m "feat(area): what changed"
# adds: Signed-off-by: Your Name <you@example.com>
```

The DCO check rejects unsigned commits. Keep commits ticket-scoped and reference the issue
(`Fixes #NN`) in the commit body.

## Security

Report vulnerabilities privately per [SECURITY.md](SECURITY.md) — never in a public issue.
Credentials are references only: the broker resolves them at the moment-of-use and injects at
egress. **A real secret must never be rendered into agent context, arguments, logs, or events,
and an unavailable backend must fail closed — never falling back to a static secret.**

## Scope

v0.1.0 is PRD 04 §P0 (R1–R7) only: the reference model, keychain + credential-file backends,
egress injection, the token model, `revoke`, lifecycle events, and secret-evasion detection. Step-up
issuance (R9), stdio-server specialization (R10), and the P2 slate are explicitly out of scope until
v0.1.0 ships.
