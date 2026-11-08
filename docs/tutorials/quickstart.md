# Quickstart — first brokered credential in 15 minutes

> **Status: design of record.** These are the designed v0.1.0 commands — the plan of record the build and
> the step test are held to. When v0.1.0 ships, `tests/docs/test_quickstart.py` replays this page's exact
> commands end-to-end (< 15 min) and the page may not drift from the CLI
> ([docs plan](../plans/docs-plan.md)). Until then, every step below is *documented*, not *field-tested*.

**BLUF:** Install → scan → migrate one secret → make a real authenticated tool call where the agent never
sees the credential → dump the agent's entire context and find **nothing usable** → revoke and watch the
replay fail in under a second. Fifteen minutes, one machine, no cloud account, no code changes.

## Before you start

- macOS or Linux. `pip` available. One Tier-1 harness installed (Claude Code for recipe #1).
- **No real secrets needed:** use a throwaway token for a sandbox account. Nothing in this flow ever
  prints a secret value — that is the product working, not a missing feature.
- Timeboxes below assume the [quickstart path](../guides/adoption-paths.md); if you get stuck,
  `agentkeys doctor` explains the effective config and the most recent denial.

## Minutes 0–3 — install and init

```sh
pip install agentsec-agentkeys
agentkeys init            # writes a minimal config: keychain backend, monitor-safe defaults
agentkeys doctor          # effective backends, TTL bands, capability flags, clock — all green?
```

`init` refuses to guess: if the config is ambiguous, it fails with the field named — that is fail-closed
(E4), not a bug.

## Minutes 3–6 — find and migrate one secret

```sh
agentkeys scan            # masked previews only: .env, mcp.json, scripts — never the value
agentkeys migrate .mcp.json GITHUB_TOKEN --backend keychain
```

`migrate` moves the value into the keychain, rewrites every use site to
`"GITHUB_TOKEN": "akref:keychain/agentkeys/dev/github-pat"`, and deletes the literal from the file
(R17). Re-run `scan` — the finding is closed.

## Minutes 6–9 — the brokered call (Claude Code recipe)

```sh
claude                    # run your agent; its MCP server was already launched under the broker wrapper
```

Ask the agent to do something that needs the token. The tool call authenticates — and the transcript
contains **only the reference** (R2, SC-12). No code changed; the harness was never touched
([recipe](../prd/16-adapters-and-integration.md)).

## Minutes 9–11 — proof #1: nothing to steal

```sh
agentkeys context-dump --session latest | agentkeys scan-usable
# 0 usable credentials found in transcript/env/args/config/logs
```

This is the **never-in-context invariant** (R1, [SC-40](../prd/17-scenarios.md)) — the same attack pack
that runs in CI on every release. A simulated full compromise of the agent's world finds references and
fake test values, nothing usable.

## Minutes 11–13 — proof #2: the one-second kill

```sh
agentkeys revoke --agent claude-code
agentkeys replay --last
# revoked in 0.19s · replay of pre-revoke token: REFUSED (exchange-rejected)
```

End-to-end by definition: t0 is the moment the revoke dispatches; t1 is the moment a **replay of the
pre-revoke credential fails** (R4, [SC-24](../prd/17-scenarios.md)). A fast command with a still-live
token would be a false green — the replay is the proof.

## Minutes 13–15 — the evidence

```sh
agentkeys export --session latest      # deterministic, secret-free JSONL lifecycle
agentkeys verify-log                   # hash chain verifies
```

Every issuance, use, and revocation is attributed and tamper-evident (R6, E12) — this is what an auditor
(or [agentcomply](https://github.com/agentic-suite)) consumes.

## What just happened

| Step | The property you just exercised |
|---|---|
| scan/migrate | The credential left the agent's **readable world** — [R17](../prd/05-features.md) |
| Brokered call | Resolution at moment-of-use, injection at **egress** — [R2](../prd/05-features.md) |
| Context dump | **Zero usable secrets** — the permanent invariant [R1](../prd/05-features.md) |
| Revoke + replay | Unconditional kill, **≤1s**, replay-verified — [R4](../prd/05-features.md) |
| Export + verify | Attributed, **hash-chained** lifecycle — [R6](../prd/05-features.md) |

## If something went wrong

| Symptom | Meaning | Fix |
|---|---|---|
| `doctor`: backend locked | Keychain locked — issuance denied (fail-closed) | Unlock; never bridge with a literal secret ([rb-1](../prd/22-operations-and-governance.md)) |
| Call failed: `exchange-rejected` | Binding mismatch — wrong audience/tool for the reference | Check the binding config; `doctor` names the mismatch |
| Scan found nothing | No candidates in the scanned roots — or all migrated | Success looks like this after migrating |
| Replay still succeeds after revoke | **A real bug** — the one thing we never ship | File it; SC-24 is a release-blocking gate |

## Next steps

- [Adoption paths](../guides/adoption-paths.md) — solo → team → CI.
- [Demo scripts](../guides/demo-scripts.md) — the three demos, ready to run for an audience.
- [Why brokers, not detectors](../explanation/why-brokers-not-detectors.md) — the argument behind all of it.
- [The PRD set](../prd/README.md) — the plan of record, top to bottom.
