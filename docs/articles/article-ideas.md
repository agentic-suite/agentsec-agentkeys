# Article ideas — agentkeys v0.1.0 field test

These are the **best Dev.to candidates** from the field-test work: educational,
engaging, and grounded in reusable engineering lessons — **not** “look at my
mistake” stories.

Each entry keeps three things only:
- a strong title,
- a reader-facing hook,
- grounding facts from the committed field evidence.

Full source material:
- [field test report](../field-test/v0.1.0/FIELD_TEST_REPORT.md)
- [field test plan](../field-test/v0.1.0/FIELD_TEST_PLAN.md)
- [traceability](../field-test/v0.1.0/TRACEABILITY.md)
- [published benchmark pack](../../bench/README.md)

---

## 1. Exit Code 0 Is the Weakest Evidence You Have

**Title.** Exit Code 0 Is the Weakest Evidence You Have — Make Your Verifier Re-Derive Every Claim

**Stronger alternate title.** Your Green Build Proves Less Than You Think

**Core promise.** Most engineering teams still trust the easiest signal in the room: “the command passed.”
This article argues that **process success is not evidence success**. If a claim matters — security, correctness,
compliance, performance, migration safety, anything release-blocking — the checker should re-derive the claim
from the emitted artifacts instead of trusting the runner’s own verdict.

**Reader hook.** We have all seen this failure mode: a script exits 0, CI goes green, and everyone relaxes.
But a green process can hide the exact thing you care about:
- an assertion encoded with the wrong belief,
- an evidence file that was never written,
- an output that says “passed” while the artifact contradicts it,
- a summary that claims success but cannot be re-checked independently.

The article should open by challenging a familiar assumption: **an exit code only tells you that a program
finished in the way its author defined as success**. It does not tell you the claim is true.

**Why this is unique.** A lot of writing says “write better tests” or “add more observability.” This article is
more specific and stronger: **make the verifier distrust the test runner itself**. That is a memorable, reusable
 idea for infra, security, AI evals, benchmarking, and CI design.

**Why a Dev.to reader should care.**
- CI pipelines trust command success too easily.
- Benchmark posts often trust one script’s self-reported number.
- Security checks frequently stop at “scanner returned 0 findings” without re-checking the emitted evidence.
- AI/eval workflows often trust model-run summaries rather than their underlying traces.

This idea generalizes far beyond this repo.

**Proposed article shape.**
1. **The bad default:** why exit code 0 feels authoritative.
2. **Why it fails:** a program can be internally consistent and still prove the wrong thing.
3. **The better pattern:** separate the runner from the verifier.
4. **What to re-derive:** assertion math, file hashes, required artifacts, minimum assertion depth, schema,
   traceability, and status/limitation rules.
5. **What this changes culturally:** green now means “independently checkable,” not “script says okay.”
6. **A checklist readers can steal** for their own pipelines.

**Important points to develop in the article.**
- A runner should be allowed to be wrong; the verifier exists to catch that.
- Verification should be **artifact-first**, not log-first.
- The checker should recompute `passed` from `kind`, `expected`, and `actual`.
- Evidence files should be present, hashed, and tied back to the summary.
- A PASS with shallow or missing assertions should itself fail verification.
- A self-test for the verifier is part of the design; otherwise you are just moving blind trust one layer over.

**Grounding facts.**
- Gate: `scripts/fieldtest/check_grounding.py` re-derives every assertion from committed results.
- Final sweep: `findings = 0` across all 74 results.
- Minimum evidence depth enforced: ≥2 assertions per case, ≥3 for the five blocking scenarios.
- PASS with no grounded assertions is itself a finding.
- Evidence files are hash-checked, not merely expected to exist.
- The harness self-test runs only on temp copies, never on the real report/results tree.

**Closing angle.** The memorable line for the article is: **“A green process is only a suggestion. A
re-derived claim is evidence.”**

---

## 2. Most Performance Benchmarks Are Too Easy to Game

**Title.** Most Performance Benchmarks Are Too Easy to Game — Here’s How to Publish One That Isn’t

**Stronger alternate title.** How to Publish a Performance Claim Nobody Can Game

**Core promise.** This article is not “look how fast my system is.” It is about a harder and more useful
question: **what would make a performance claim credible even to a skeptic?** The answer is not a pretty p95.
It is a protocol that makes self-deception difficult.

**Reader hook.** Most benchmarks fail before the number even appears. The timer starts too late, stops too
early, measures the command instead of the effect, drops the slowest runs, hides the machine class, or publishes
only a percentile that flatters the system. That is why so many benchmark posts feel like marketing even when
the author is sincere.

This article should position itself as a practical answer to that skepticism: **how do you structure a
performance test so even you cannot accidentally game it?**

**Why this is unique.** Plenty of benchmark posts publish numbers. Fewer publish the anti-gaming method. That
method is the real article.

**Why a Dev.to reader should care.** Anyone shipping an API, broker, cache, auth system, queue, or infra tool
can borrow the same template for:
- latency claims,
- revoke / invalidate / cache-expiry claims,
- warmup and cold-start claims,
- failover or restart claims,
- throughput ceilings,
- “eventually consistent within X seconds” claims.

**Proposed article shape.**
1. **Why most benchmark posts feel untrustworthy.**
2. **The common failure modes:** bad timer boundaries, wrong success condition, percentile-only reporting,
   no replay check, no hardware disclosure.
3. **The anti-gaming protocol:**
   - start the timer at the real event boundary,
   - stop the timer at the externally visible effect,
   - verify the effect, not the command,
   - report max as well as p95,
   - run enough iterations,
   - publish machine class and re-run instructions.
4. **Why “max” matters:** one catastrophic outlier can be the real story.
5. **Why independent reproduction matters:** field-tested is not the same as verified.
6. **A reusable benchmark template** readers can lift into their own repos.

**Important points to develop in the article.**
- A performance claim should be written as a falsifiable statement, not a bragging number.
- You should measure the thing the user experiences, not an internal convenience metric.
- A fast revoke command is meaningless if the old credential still works for a while after.
- p95 alone can hide the run that actually matters; max tells you whether the budget was ever breached.
- Machine disclosure is not optional if you want readers to reason about transferability.
- Re-run instructions matter because claims get stronger when someone else can reproduce them.

**Grounding facts.**
- Claim under test: revoke kills access in ≤1 second end-to-end.
- Published pack: `bench/results/killtime-contextdump.json` with README in `bench/README.md`.
- Result: p50 **0.012ms**, p95 **0.016833ms**, max **0.030667ms**, N=100; replay failures = 100/100.
- PASS requires both p95 ≤ 1s **and** max ≤ 1s — not a flattering percentile alone.
- The measurement verifies replay refusal, not just revoke dispatch time.
- The published pack includes machine details and a re-run procedure so the claim can later move toward
  independent verification.

**Closing angle.** The article should end on a strong distinction: **a benchmark number is interesting; a
benchmark protocol is useful.**

---

## 3. Your Test Dashboard Lies by Omission

**Title.** Your Test Dashboard Lies by Omission — Here’s a Better Verdict Vocabulary

**Stronger alternate title.** Your Green Dashboard Is Hiding the Most Important Rows

**Core promise.** A dashboard full of green can still be low-trust if it erases the context a reader actually
needs. This article argues that **verdict vocabulary is part of the engineering system**. If a report cannot
distinguish “passed,” “failed,” “warned with a real limitation,” and “not run with a reason,” then it is
optimizing for neatness over truth.

**Reader hook.** We have all read dashboards that say some version of “97% passing” and leave the reader to dig
through logs to find the only three cases that matter. The core frustration is not lack of data; it is bad
compression. The report flattened meaningful differences into one pleasant-looking status line.

The article should push a stronger idea: **test reporting is not the final coat of paint. It is part of the
control plane for release decisions.** If the vocabulary is weak, the decision quality is weak.

**Why this is unique.** A lot of writing talks about writing more tests. Much less talks about writing better
verdicts. This article is about the semantics of outcomes: how to tell the truth without drowning the reader.

**Why a Dev.to reader should care.**
- Release dashboards often hide risk in summary percentages.
- Engineering teams need a shared way to talk about conditional truth.
- Ops, QA, platform, and security reports all suffer when every outcome is forced into pass/fail.

**Proposed article shape.**
1. **The lie of compression:** why one number or one color is often too lossy.
2. **The missing states:** why WARN and NOT RUN are necessary, not messy.
3. **What a verdict should carry:** status, reason, limitation, evidence, and claim label.
4. **How better vocabulary improves decisions:** the reader knows whether to ship, investigate, defer, or
   rerun.
5. **What not to do:** percentages with no row-level accountability.
6. **A compact template** readers can reuse for dashboards and release reports.

**Important points to develop in the article.**
- PASS should mean independently grounded, not merely “no exception happened.”
- WARN should mean “true, with a named boundary,” not “we wanted yellow.”
- NOT RUN should be explicit and justified, not hidden as missing data.
- Blocking cases may need stricter status rules than informational cases.
- One-line notes matter because leaders and reviewers often read the summary table first.

**Grounding facts.**
- Final field verdicts: **71 PASS · 0 FAIL · 3 WARN · 0 NOT RUN** across 74 cases.
- The report’s master table records every case id with status and a one-line note.
- WARN is allowed only for WARN-eligible classes and requires a named limitation.
- The five blocking scenarios may never WARN; all five finished PASS.
- The report stays at the correct claim label: *field-tested*, not *verified*.

**Closing angle.** A useful line for the ending: **“A test report is not a scoreboard. It is a decision
document.”**

---

## 4. The Claims Ladder: Documented, Conformance, Field-Tested, Verified

**Title.** The Claims Ladder: Documented, Conformance, Field-Tested, Verified

**Stronger alternate title.** Don’t Call It Verified Until Someone Else Reproduces It

**Core promise.** This article gives readers a stricter language for technical claims. The main idea is simple:
**use the strongest word your evidence supports, and no stronger.** Most teams unintentionally overstate by
collapsing different grades of support into the same label.

**Reader hook.** Words like “tested,” “proven,” and “verified” sound precise but often hide very different kinds
of evidence. A feature can be documented without ever being exercised. A suite can pass without a real-world
trial. A field trial can succeed once without becoming independently reproducible. That ambiguity hurts release
notes, blog posts, README claims, and even incident reviews.

This article should present a memorable four-rung ladder that readers can apply immediately:
- **Documented** — written and specified.
- **Conformance** — the relevant suite passed.
- **Field-tested** — a human entered a verdict against committed evidence.
- **Verified** — an independent third party reproduced the claim.

**Why this is unique.** The article is not just about “be honest.” It gives a concrete taxonomy that can clean up
how teams talk about reliability, compliance, performance, and security.

**Why a Dev.to reader should care.**
- README and docs claims are often stronger than the evidence behind them.
- Teams need a vocabulary for release notes and benchmark posts that does not drift into marketing.
- Open-source maintainers can use this to make promises more credible.

**Proposed article shape.**
1. **Why the current language is sloppy.**
2. **The four labels and what each one really means.**
3. **Examples of mislabeling:** where teams say “verified” but only mean “we ran it once.”
4. **How to label claims in practice:** performance, standards, field usage, and security.
5. **Why the distinction improves trust instead of weakening the story.**
6. **A small claims-audit template** readers can add to release notes or benchmarks.

**Important points to develop in the article.**
- A stronger claim label is not a compliment; it is an evidence category.
- “Field-tested” is already meaningful and should not be treated as inferior marketing.
- “Verified” should be rare and valuable because it means independent reproduction.
- Claims become more trustworthy when the downgrade path is explicit.
- This vocabulary is useful precisely because it is slightly stricter than normal engineering speech.

**Grounding facts.**
- The report includes a claims-label audit mapping promoted claims to their label and evidence.
- Kill-time ≤1s is labeled *field-tested*.
- Standards/RFC rows are labeled *conformance*.
- Nothing is yet labeled *verified* because no independent third party has re-run the published pack.
- The benchmark pack exists specifically to let a claim move from field-tested to verified later.

**Closing angle.** End with the line: **“Trust grows when your labels get stricter, not louder.”**

---

## 5. Why PASS/FAIL Is Not Enough for Real-World Testing

**Title.** Why PASS/FAIL Is Not Enough for Real-World Testing

**Stronger alternate title.** PASS/FAIL Is Too Crude for Real Systems

**Core promise.** Binary status reporting is emotionally satisfying and operationally weak. This article makes
the case that real systems need a third honest category: **works, but with a named limitation that remains part
of the verdict**. Without that, teams either overstate readiness or bury important caveats in prose nobody reads.

**Reader hook.** Engineers are trained to love crisp outcomes: pass or fail, green or red, yes or no. But many
important truths are conditional. A workflow might be correct but only on one surface. A measurement might be
valid but not yet independently reproduced. A live integration may be wired correctly but blocked by external
auth state. If the only allowed statuses are pass and fail, the report will lie somewhere.

**Why this is unique.** This is not a generic “nuance matters” essay. It gives a disciplined argument for why
WARN should exist, what rules should govern it, and how to stop it from turning into a dumping ground.

**Why a Dev.to reader should care.**
- Release gates frequently need a truthful middle state.
- Platform support matrices often have real caveats that should not be hidden.
- Integration and field reports become more useful when limitations stay attached to the verdict.

**Proposed article shape.**
1. **Why teams overuse pass/fail.**
2. **Where binary status breaks down in practice.**
3. **What a disciplined WARN means:** not vague concern, but truth with a named boundary.
4. **Rules that keep WARN honest:** eligibility, required limitations, and hard no-WARN zones.
5. **When a WARN should be upgraded to PASS:** only after the missing proof or missing control exists.
6. **A practical status policy** readers can adopt.

**Important points to develop in the article.**
- WARN should never mean “we are unsure.” It should mean “the claim is bounded in this explicit way.”
- Some scenarios are too important to allow WARN at all.
- Limitations should be machine-visible, not buried in paragraph text.
- A WARN should create pressure to either tighten the test or narrow the claim.
- The existence of WARN makes PASS stronger, because PASS now means the limitation is truly gone.

**Grounding facts.**
- Final state includes exactly **3 WARN**, each with a named limitation.
- Remaining WARNs are honest environment limitations, not silent failures:
  - fresh-machine install median still lacks a naive-human run,
  - Claude Code is installed but not logged in headlessly,
  - Cursor has no headless surface on this box.
- One earlier WARN (`FT-EV-ENFORCE`) was upgraded to PASS only after composing a real OS-backed deny check.
- The rules enforce that WARN cannot appear without a limitation, and cannot be used for the five blocking cases.

**Closing angle.** The article should land on: **“A truthful middle state makes your green states more
trustworthy.”**

---

## 6. The Test Itself Is Part of the Product

**Title.** The Test Itself Is Part of the Product — Especially for Security and Infra Tools

**Stronger alternate title.** Your Test Harness Is Part of the Security Boundary

**Core promise.** For infra, platform, and security tooling, the test harness is not a disposable wrapper around
the “real” product. It participates directly in the trust claim. If the harness can leak a secret, mislabel a
result, overwrite a human report, or smooth over a bad outcome, then the evidence it emits is weaker than the
feature it is supposed to validate.

**Reader hook.** Teams often treat harness code as second-class: a few scripts, a temp report generator, some
glue around Docker, maybe a smoke check or two. But when the product’s value proposition is security, safety,
or controlled access, **the harness becomes part of the proof surface**. Readers should come away with a bigger
idea: a trustworthy test harness has its own invariants, its own attack surface, and its own quality bar.

**Why this is unique.** Many articles say “test your tests.” This one is sharper: **for trust-sensitive tools,
the harness is itself part of the product boundary.** That is a stronger and more memorable claim.

**Why a Dev.to reader should care.**
- Security tools can be undermined by sloppy evidence handling.
- Infra tools live or die on trust, reproducibility, and operator confidence.
- Harness design matters for any project where the proof is as important as the feature.

**Proposed article shape.**
1. **Why harnesses are usually under-designed.**
2. **What can go wrong when the harness is weak:** secret leaks, false greens, artifact drift, report clobbering.
3. **What harness invariants look like in practice:** grounding, leak scanning, traceability, report guards,
   self-tests, and independent benchmark packs.
4. **Why this matters more for infra/security than for ordinary app features.**
5. **How to raise the harness to product quality:** tests, coverage, static checks, and refusal behavior.
6. **A practical checklist** for readers maintaining their own tooling.

**Important points to develop in the article.**
- Evidence quality can be degraded by tooling even when product logic is correct.
- Human-maintained artifacts sometimes need explicit code-level protection.
- A benchmark pack should be treated as a product surface, not a throwaway export.
- Traceability is not bureaucracy; it is how you preserve meaning between claim, case, result, and report.
- If a harness can silently lower the truth standard, it belongs inside the engineering threat model.

**Grounding facts.**
- The field-test tooling shipped with its own gates: grounding, leak scan, traceability, and harness self-test.
- The hand-maintained report is protected by code and tests; automation refuses the canonical report path.
- The published benchmark pack is machine-readable and tied back to committed results.
- Final M14 gate: **743 passed**, `ruff` clean, `mypy --strict` clean, coverage **95.22%**.
- The strongest lessons from the sweep improved the harness and the reporting discipline, not just the product code.

**Closing angle.** A strong final line: **“If your tool sells trust, your harness is part of what you are
selling.”**
