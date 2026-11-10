# Demo scripts — the three demos

**BLUF:** These are the three agentkeys demos, in the order that lands hardest: **the one-second kill**
(the incident response), **nothing to steal** (the context-dump proof), and **the stdio flagship** (the
thing nobody else has). Each maps to gated scenarios — they are **written runs of the packs, not
cherry-picked screens**; if a demo fails in rehearsal, the scenario is red, and that is the demo's answer.
A 60-second comment-section version is at the bottom. None of these demos contains a real secret — by
design, that is the point.

**Status:** the **scenarios behind these demos are field-tested** — FT-RK-KILLTIME (kill-time), FT-AP-CONTEXTDUMP
(nothing to steal) and FT-ST-NOSECRET (the stdio flagship) are PASS in the
[hand-maintained report](../field-test/v0.1.0/FIELD_TEST_REPORT.md). The demo *scripts* themselves
have **not yet rehearsed** end-to-end on a fresh machine; they are written runs of gated packs, so treat a
failed rehearsal as a red scenario, not as a bad demo.

**Rehearsal record.** The three backing packs were re-run on the release-candidate commit
(`4d6b85e`) into a throwaway results directory — `killtime`, `attack`, `stdio`: **12 PASS · 0 FAIL · 0 WARN**
(FT-RK-*, FT-AP-*, FT-ST-*). The demo *scripts* below are still unrehearsed as performances; the scenarios they
rest on are green.

---

## Demo 1 — "Revoke the agent, not the quarter"

**The sentence it plants:** *when an agent goes wrong, you stop it with a command, not a rotation
project.* — [SC-24](../prd/17-scenarios.md) (blocking)

**Setup (5 min before):** one migrated credential; a live session mid-call; a terminal the audience can
see.

**Script:**

1. Show the agent making a real authenticated tool call (the token works).
2. Say: *"It's 3 a.m. and this agent just started exfiltrating. What do you do today?"* — let them answer
   (rotate everything, hunt tokens, pull network access…).
3. `agentkeys revoke --agent claude-code`
4. `agentkeys replay --last` → **REFUSED (`exchange-rejected`)** — show the measured time.
5. Show the `revoked` event: scope, target, **operator identity**, `effective_at`.

**What they see:** the credential dies in **under a second**, the replay proves it, and the audit names
who pulled the trigger. No rotation, no waiting for a grant to expire.

**Honesty note:** say out loud that the ≤1s number is measured end-to-end (revoke → *replay fails*), in
CI, on every release — that this run measured p50 0.012ms / p95 0.017ms / max 0.031ms at N=100 with 100/100
replays refused (FT-RK-KILLTIME) — and that the [benchmark](../../bench/README.md) is public so they can
re-run it. Say plainly that one box's number is not a fleet claim.

---

## Demo 2 — "Nothing to steal"

**The sentence it plants:** *a prompt injection can't exfiltrate what isn't there.* —
[SC-40](../prd/17-scenarios.md) + [SC-43](../prd/17-scenarios.md) (both blocking)

**Setup:** a seeded session — one migrated credential in active use, plus a deliberately planted
canary-shaped fake in an `.env` (the scanner-sensitivity control: if the pack finds **nothing**, the
demo is a harness failure, not a pass).

**Script:**

1. "Your agent is compromised. The attacker dumps **everything**: transcript, env, arguments, config,
   logs." — run `agentkeys context-dump --session latest | agentkeys scan-usable`.
2. Show the result: **0 usable credentials** — references and clearly-fake values only.
3. Point at a reference on screen: *"That's all the agent ever held. It's safe to log. Try to use it
   without the broker — it's just a name."*
4. Optional gut-punch: run the same scan against the **pre-migration** fixture (the old `.env`-with-token
   copy) — it lights up. *That was your setup yesterday.*

**What they see:** the invariant, demonstrated rather than asserted — with the falsification control
visible (a seeded secret **must** be caught; a scanner that finds nothing proves nothing).

**Honesty note:** we don't claim injection is solved — we claim injection **has nothing to steal**.
Detection products can't demo this; there's nothing to detect after the architecture is right.

---

## Demo 3 — "The stdio flagship"

**The sentence it plants:** *the MCP spec tells local servers to read credentials from the environment —
we're the ones who fixed that.* — [SC-12](../prd/17-scenarios.md)/[SC-13](../prd/17-scenarios.md);
coverage-map **row #8: nobody**.

**Setup:** a stock community MCP server (e.g., a GitHub one) configured the way everyone configures it —
normally with a literal token in `mcp.json`.

**Script:**

1. Show the familiar config: `mcp.json` with a real token pasted in. *"This is the default on every
   machine in your org. The agent can read this file."*
2. `agentkeys migrate .mcp.json GITHUB_TOKEN` → the config now holds
   `"akref:keychain/agentkeys/dev/github-pat"`. The server was **relaunched under the broker wrapper**.
3. Ask the agent to use the tool — **it succeeds**. The upstream got a broker-minted, audience-bound
   token; the client's token was never forwarded (no passthrough, E14).
4. `cat` the config, dump the env, scan the transcript: no secret anywhere in the server's world.
5. Kill it live: `agentkeys revoke --session <that-server>` → the next tool call fails closed.

**What they see:** a stock server, zero code changes, secrets gone from config/env/context — and the
pattern being proposed upstream to MCP ext-auth ([PRD 20 §3](../prd/20-standards-and-claims.md)).

**Honesty note:** name the boundary — a server co-located in the same readable runtime as arbitrary
agent code is the documented hard case ([PRD 06 §4](../prd/06-security-baseline.md)); the demo uses the
wrapper's process boundary and says so.

---

## The 60-second version (for a comment section)

> Your agent's context has an API key in it. Inject the agent and you own prod — and "revoke" means a
> quarter of rotation. agentkeys: the agent holds a **reference**, the key stays in your keychain, a
> short-lived audience-bound token is injected at egress — dump the whole context and there's **nothing
> usable to steal**. `agentkeys revoke` kills every credential the agent holds in **<1s, replay-verified
> in CI**. Local-first, OSS, works on stdio MCP servers nobody else covers. The kill-time benchmark is
> public — re-run it yourself. [README →]

---

## Rules for running these

1. **Rehearse against the packs** — the demos are the scenarios; a red scenario cancels the demo, it
   doesn't get a workaround.
2. **No real secrets, ever** — in the config, the transcript, or the muscle memory of the audience.
3. **Show the failure paths too** — a locked keychain denying issuance is a *feature* demo (fail-closed);
   hiding it would be the over-claim the [claims vocabulary](../prd/20-standards-and-claims.md) forbids.
4. **Enter drill results by hand** — if a demo doubles as a drill, its verdict goes in the
   hand-maintained report, never an auto-generated one.
