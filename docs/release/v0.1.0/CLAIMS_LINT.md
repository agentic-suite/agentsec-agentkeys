# Claims lint — result (`15.2`)

**BLUF:** **18 claims, 0 findings.** Every public claim in the release resolves to a committed field result, and
no claim wears a label above its evidence. **Nothing is labelled *verified*.** The prose scan of the public docs
finds no unsupported superlative.

- **Gate:** `python -m agentkeys.release claims --root .` (exit `0` = green)
- **Ledger:** [CLAIMS.md](CLAIMS.md) · **Vocabulary:** [PRD 20 §6–§6a](../../prd/20-standards-and-claims.md)
- **Run on:** commit `0b57a01` · 18 ledger rows · 0 findings

---

## 1. What is checked

| Check | Rule | Why it exists |
|---|---|---|
| **Label is in the ladder** | `documented` < `conformance` < `field-tested` < `verified` | an invented label (`production-grade`) is an escape hatch; it is a finding, not a synonym |
| **Evidence resolves** | any label above `documented` names a case id that exists in `field-test/v0.1.0/results/` | a label pointing at nothing is a wish |
| **Evidence is green** | `fail` / `not-run` evidence cannot support a claim | a red case is not a claim |
| **WARN caps the label** | WARN evidence earns `documented`, never `field-tested`, and **must state its limitation** | a bounded truth is not a full one; the limitation is the label's fine print |
| **`verified` needs a third party** | `third_party = yes` required | definitional: verified means *someone else reproduced it* |
| **Prose superlatives** | banned terms (`certified`, `militarily`, `enterprise-grade`, …) fail unless the sentence is a non-claim | you cannot label a sentence that has no evidence behind it |
| **Non-claims stay said** | the "not a certification / not a detector / not a PoP system / not a vault" block is required | honesty that disappears under deadline is not honesty |

## 2. The result

```
ledger claims: 18
claims lint: PASS — no claim wears a label above its evidence
```

| Label | Count | Examples |
|---|---|---|
| `field-tested` | 12 | revoke ≤1s; 0 usable in the context dump; no secrets in ledger/export; scan/migrate recall; stdio no-secret; bindings refuse replay; fail-closed matrix; evasion; offline/air-gap; NFR targets; stdlib-only; the report guard |
| `conformance` | 1 | RFC 8693/8707/9700/9728/9068/7636 (DPoP explicitly not supported) |
| `documented` | 5 | install < 15 min (WARN); ≥2 Tier-1 recipes (WARN); Copilot lower-layer; Tier-2/3 support; third-party reproduction |
| `verified` | **0** | — |

## 3. The two claims that could not be promoted — and why

Both are `WARN` results, both keep their limitation attached, and neither was smoothed into a stronger label:

1. **Install → first brokered call < 15 min** — the scripted median (0.54s) and a fresh-venv path (2.7s) are
   green, but a **naive human on a fresh machine** has not been measured. That specific gap is the claim.
2. **≥2 Tier-1 harness recipes end in a verified authenticated call** — wiring and smoke are green for Claude
   Code and Cursor; the live legs are blocked (`claude` is installed but not logged in headlessly; Cursor has no
   headless surface). Blocked is not passed.

If either gap closes with real evidence, the row moves up the ladder with its case id. Nothing else changes.

## 4. What the lint cannot do

- It checks the **claims we recorded**, not every sentence ever written. A claim invented in a blog post or a
  tweet is outside its reach — which is why the blocklist exists as a backstop for the public docs.
- The banned-term list is deliberately short and blunt. It catches the words that assert a standing we do not
  have; it cannot catch a subtly misleading sentence that uses only permitted words.
- It does not verify the *quality* of a pack. If a pack is weak, the label is still only as good as the pack —
  the field test and its hand-entered verdicts are where that judgement lives.
