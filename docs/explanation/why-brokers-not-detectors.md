# Why brokers, not detectors

**BLUF:** The agent-security market sells detection — classifiers that watch for malicious prompts and
suspicious behavior. The incident record says detection keeps losing, and the research consensus says it
will keep losing, because the problem is **architectural**: an agent with a real credential in its
context is a vault with the door open, and no amount of watching changes that. agentkeys is the other
school: **remove the thing worth stealing**, bind what remains to one audience, one tool, one session —
and make it die on command. This doc is the argument, with its evidence and its honest limits.

**Status:** explanation (Diátaxis *why*) — the positions are argued in
[PRD 01](../prd/01-why.md) and [PRD 06](../prd/06-security-baseline.md).

## 1. The incidents are all the same incident

Every serious documented case — in-the-wild prompt injection exfiltrating production API keys
(Anthropic threat-intel, Sept 2026), MCP tool poisoning and rug-pulls, the coding-agent supply-chain
RCE — shares one shape: **the credential was already inside the agent's world, and the attack only had to
read it out.** The agent was the vault, the context was the door, and the "security" around it was a
guess about intent.

28.65 million hardcoded secrets were added to public GitHub in a single year, with AI-service
credentials the fastest-growing class (GitGuardian 2026). The door isn't closing on its own.

## 2. Detection has an empirical ceiling, and it's low

- **AgentDojo** (NeurIPS 2024): simple injection attacks retain roughly **46% success against some of
  the best available defenses** — and the maintainers refuse to call the leaderboard fair.
- **InjecAgent**: one hacking prompt nearly **doubles** attack success on ReAct-style agents.
- The design-patterns literature (IBM/Invariant/ETH/Google/Microsoft) is blunt: the credible defenses
  are **architectural** — context minimization, separation, capability scoping. Nobody credible claims
  injection is *solved*; DeepMind's CaMeL, the best-known attempt, is itself a dual-LLM construction.

A detector is a probability. A broker is a **property**: the context either contains a usable credential
or it doesn't, and that is checkable — which is why our headline proofs are a **context dump that finds
zero** and a **replay that fails**, not a detection rate.

## 3. The consensus defense is a broker, whatever it's called

Strip the vendor decks and every credible recommendation converges on the same short list: **short-lived,
capability-scoped, session-bound credentials, resolved at the moment of use, revocable centrally**. That
is not a feature of a detection product — that is a *broker*. Aembit says it in identity language;
1Password says it in vault language; the IETF's WIMSE/AIMS draft says it in standards language;
the secretless pattern (CyberArk, iron-proxy, secretless-ai) says it in open-source language. The
disagreement is only about who runs it and what it costs.

## 4. Why revocation is the tell

Revocation is the weakest capability in the entire agent-security landscape (coverage map row #7:
commercial ●●○, OSS ●○○). Detection vendors don't ship it because **you cannot detect your way to a dead
credential** — a kill switch has to be *in the credential's lifecycle*, not observing it. If a product
can't revoke in one command, it was never holding the keys; it was watching someone else hold them.

## 5. What the broker costs (honestly)

| Cost | The deal |
|---|---|
| **A process to trust** | The broker is now a target — the highest-value one on the machine. That's why its own threat model is published, the secrets live in *your* keychain (never in our database), and the tamper cases are CI fixtures ([PRD 06 §3](../prd/06-security-baseline.md)) |
| **The stdio boundary** | A subprocess sharing the agent's readable runtime cannot be fully protected; we require a process boundary and say so when it can't be had ([PRD 06 §4](../prd/06-security-baseline.md)) |
| **Bearer tokens until DPoP** | v0.1.0 tokens are stolen-string-usable within their short, bound, single-use life; proof-of-possession lands at R14 — labeled, not implied ([PRD 20 §2a](../prd/20-standards-and-claims.md)) |
| **Adoption effort** | Migration is the tax; that's why `scan`/`migrate` exists — the broker has to be *easier* than pasting the key ([R17](../prd/05-features.md)) |
| **Fail-closed UX** | A locked keychain denies the call. That annoyance is the security property; the runbook says unlock, never bridge ([rb-1](../prd/22-operations-and-governance.md)) |

## 6. What the broker buys

1. **Injection becomes not worth it** — the prize is gone from the context; what remains is a
   single-use, minutes-scale, one-audience token that dies with the session.
2. **Incident response becomes one command** — revoke beats rotation by a quarter.
3. **Oversight becomes enforceable** — prod-class scope cannot even *mint* without a human approval
   (the EU AI Act Art. 14 story, [PRD 20 §4a](../prd/20-standards-and-claims.md)).
4. **The audit becomes an artifact** — a hash-chained lifecycle, joined to the session trace, instead
   of a log line that says "used a credential."
5. **The claims become checkable** — zero-usable-secrets and ≤1s are falsifiable, published, and
   re-runnable ([PRD 21](../prd/21-evidence-register-and-method.md)). Detection-rate claims are not.

## The one-sentence version

> Detection asks "was that the agent misbehaving?" — the broker makes the question irrelevant by asking
> a better one first: *"why does the agent have a real key at all?"*

## Related

- The failure modes and evidence: [PRD 01 — Why](../prd/01-why.md)
- The invariants and our own threat model: [PRD 06](../prd/06-security-baseline.md)
- The proofs and how to re-run them: [PRD 21](../prd/21-evidence-register-and-method.md)
- See it live: [Quickstart](../tutorials/quickstart.md) · [Demos](../guides/demo-scripts.md)
