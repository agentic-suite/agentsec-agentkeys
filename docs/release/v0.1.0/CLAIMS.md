# Claims ledger — v0.1.0

Every public claim this release makes, the label it earned, and the committed field result behind it. Linted by
`python -m agentkeys.release claims` against [PRD 20 §6–§7](../../prd/20-standards-and-claims.md).

**The ladder** ([PRD 20 §6](../../prd/20-standards-and-claims.md)):
**documented** (written, no test) → **conformance** (a spec/contract suite passes in CI) →
**field-tested** (a hand-entered verdict against committed evidence) →
**verified** (an independent third party reproduced it).

**At v0.1.0 nothing is *verified*.** That is not modesty — it is the definition. `bench/` exists so a stranger
can move a claim up the ladder; until someone does, the label stays where the evidence is.

| Claim | Label | Evidence | Third party | Note |
|---|---|---|---|---|
| `revoke` kills access end-to-end in ≤1s, replay-verified | field-tested | FT-RK-KILLTIME (p95 0.017ms, max 0.031ms, N=100; 100/100 replays refused) | no | measured on one box (macOS arm64); not a fleet claim |
| A full context dump of the agent's world yields 0 usable credentials | field-tested | FT-AP-CONTEXTDUMP | no | the seeded falsification control must fire; it did |
| No secret material in the store, exports, or ledger | field-tested | FT-AP-EVIDENCE, FT-LA-NOSECRET, FT-LA-EXPORT | no | a seeded leak fails the case naming its row |
| `scan`/`migrate`: 100% recall, 0 printed values | field-tested | FT-MP-SCANMIGRATE | no | seeded fixture only |
| A stdio child authenticates with no secret in its config, env, or transcript | field-tested | FT-ST-NOSECRET, FT-ST-NOPASSTHRU, FT-DK-BOUNDARY | no | co-located same-runtime case is a documented limit, not covered here |
| Tokens are audience-, tool-, and session-bound; replay is refused | field-tested | FT-BR-AUDIENCE, FT-BR-TOOL, FT-BR-SESSION, FT-BR-STALE | no | — |
| The broker fails closed on every operational failure | field-tested | FT-FC-ABSENT, FT-FC-CONFIG, FT-FC-STORE, FT-FC-SINK, FT-FC-CRASH, FT-FC-LOCKED | no | outage = no new issuance, never a static fallback |
| Secret evasion is detected, and enforced where an enforcer exists | field-tested | FT-EV-DOTENV, FT-EV-KEYCHAIN, FT-EV-CLOUD, FT-EV-ENFORCE | no | enforcement needs an OS/host hook; detection alone is the floor |
| RFC 8693 / 8707 / 9700 / 9728 / 9068 / 7636 conformance | conformance | FT-CONF-STANDARDS, FT-CONF-BACKENDS | no | DPoP is explicitly **not** supported at v0.1.0 |
| Offline / air-gapped operation | field-tested | FT-AG-OFFLINE, FT-DK-AIRGAP | no | the air-gap leg failed once on a harness defect, was fixed, and re-ran green |
| Performance targets (injection p99, throughput, cold start, restart, ledger, RSS) | field-tested | FT-NFR-INJECT, FT-NFR-BACKEND, FT-NFR-THROUGHPUT, FT-NFR-COLDSTART, FT-NFR-RESTART, FT-NFR-LEDGER, FT-NFR-RSS | no | this box only; the table header says so |
| No runtime dependencies (stdlib-only broker) | field-tested | FT-SC-INREPO | no | verified against `pyproject.toml` |
| The hand-maintained report cannot be written by automation | field-tested | FT-HONESTY-REPORT | no | the guard is itself a field case |
| Install → first brokered call < 15 minutes | documented | FT-CL-FIRST | no | **WARN** — scripted median 0.54s and a fresh-venv 2.7s path are green, but no naive-human fresh-box median exists |
| ≥2 Tier-1 harness recipes end in a verified authenticated call | documented | FT-HC-CLAUDE, FT-HC-CURSOR | no | **WARN** — wiring and smoke are green; the live legs are blocked (Claude Code not logged in headlessly; Cursor has no headless surface) |
| Copilot (and any closed-hook harness) coverage | documented | — | no | **lower-layer coverage** only; never a first-class hook recipe |
| Tier-2 / Tier-3 framework and platform support | documented | — | no | brokered by construction, **not** individually pack-gated |
| Everything above, reproduced by a third party | documented | — | no | nothing is verified at v0.1.0 |

## Non-claims (they must stay said)

- **Not** a compliance certification — we map to SOC 2 / ISO 42001 / EU AI Act; we are not certified.
- **Not** an injection detector — we mitigate architecturally and never claim a detection rate.
- **Not** proof-of-possession — bearer tokens until DPoP (R14).
- **Not** protection from a process sharing the agent's readable runtime (documented boundary, PRD 06 §4).
- **Not** an identity provider — we consume identity, we do not issue it.
- **Not** a vault — backends store; we broker.
