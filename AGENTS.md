# AGENTS.md — agentkeys

These rules apply to every agent/assistant session in this repository.
They are gates, not preferences.

## Field-test reports are hand-maintained — automation must never write them

- `docs/field-test/<version>/FIELD_TEST_REPORT.md` is a **hand-maintained journal**.
  Edit it by hand only.
- **No script, generator, CLI, agent, task, or automation may write, rewrite,
  regenerate, move, truncate, or delete the canonical report.** There is no
  "force" exception. This rule exists because a lossy automated rewrite has
  destroyed hand-written field notes before.
- Automated drafts, if ever added, must write a **separate**
  `FIELD_TEST_REPORT.generated.md` sibling and must refuse to overwrite any file
  carrying the `HAND-MAINTAINED` marker.
- Verdicts are entered **by hand** from the committed evidence under
  `field-test/<version>/results/`. Never infer, auto-fill, or "clean up" a
  verdict, a miss, a limitation, or a note.
- A report-guard test must assert the marker and the refusal behavior. If a
  report writer is added, the guard ships in the same change.
- Field-test **results** live under `field-test/<version>/results/`, not under
  `docs/`. `docs/field-test/<version>/` holds only the plan and the
  hand-maintained report.
- Breaching this rule is a release-blocking violation. Fix forward by hand;
  never regenerate the report from results.

Precedent: `agentpolicy` guards this with a `HAND-MAINTAINED` marker,
`build_report.py` refusing the canonical file, and
`tests/test_field_report_guard.py` locking the behavior in. Mirror that posture.

## Working rules

- Read the owning PRD/WBS and design doc before implementing a ticket.
- **Never-in-context invariant:** agents hold only *references*; a real secret is
  never rendered into agent context, arguments, or logs. Egress injection at the
  moment-of-use is the only path a plaintext credential may take. This is a
  permanent invariant, not a default.
- **Fail closed:** an unavailable, ambiguous, or misconfigured backend denies
  issuance — it never degrades to a static secret, an env fallback, or a
  long-lived token.
- Route state through the broker's store contract; every issuance, use, upgrade,
  and revocation is an append-only transition plus its `agentwatch`-schema event.
  Never write the store directly from a backend, adapter, or CLI path.
- Keep the decision boundary intact: `agentkeys` brokers and revokes credentials;
  `agentpolicy` decides whether an issuance/upgrade is approved; the enforcer
  enforces. Revocation is unconditional and never gated on policy.
- Additive contracts only: extend the token/issuance schemas; never renumber.
- Token bindings are mandatory: short-lived, audience-bound (one server),
  tool-scoped (one tool), session-bound (dies with the conversation).
- Tests first (RED → GREEN), then the milestone gate once at the end.
- Do not close an issue when the intent is to move/re-point it.
- Blocked work is marked BLOCKED with the reason; never reported as done.
