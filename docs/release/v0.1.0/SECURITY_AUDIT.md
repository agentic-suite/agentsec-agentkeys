# Security audit — secret leakage (`15.1`)

**BLUF:** **0 verified credentials** in the working tree and **0 in the full commit history** (58 commits,
all refs), verified by two independent scanners, with a planted-fake control that **fired on both**. The six
non-verified shapes that gitleaks reported in the field-test evidence are **synthetic fixtures** and are
allowlisted **by exact value** — not by path, not by shape.

- **Requirement:** [E15](../../prd/05-features.md), [PRD 06 §5](../../prd/06-security-baseline.md)
- **Gate:** `python -m agentkeys.release audit --root . --json` (exit `0` = green)
- **CI:** [`.github/workflows/release-audit.yml`](../../../.github/workflows/release-audit.yml)
- **Run on:** commit `f4266c8` · macOS arm64 · trufflehog `3.99.8` · gitleaks `8.30.1`

---

## 1. Result

| Surface | Scanner | Scope | Candidates | **Verified** | Verdict |
|---|---|---|---|---|---|
| Working tree | `trufflehog filesystem` | tracked + untracked, generated trees excluded | 4 | **0** | ✅ PASS |
| **Full history** | `trufflehog git` | every commit on every ref, **no `--since-commit` window** | 3 | **0** | ✅ PASS |
| History, 2nd ruleset | `gitleaks detect --log-opts=--all` | every commit, repo config | 0 after the narrow allowlist | **0** | ✅ PASS |
| **Control** | both | planted fake DSN + planted fake key | — | — | ✅ **both fired** |

Historical commits are searched deliberately: a credential committed and later "removed" is still a leaked
credential today, because clones and forks keep it.

---

## 2. The control (why a green result means something)

A scanner that never fires cannot certify anything, so every audit plants two fakes in a throwaway
directory and requires **both** scanners to catch theirs:

| Scanner | Planted shape | Why this shape |
|---|---|---|
| trufflehog | `postgres://control:FAKEPASSWORD0000@control.invalid:5432/control` | fires the `Postgres` detector deterministically, offline, `.invalid` never resolves |
| gitleaks | `control_api_key = 0123456789abcdef0123456789abcdef` | fires `generic-api-key` on entropy alone |

If **either** is silent the audit denies — a half-awake control is a fail
(`tests/test_release_audit.py::test_a_half_awake_control_denies_the_audit`). The control files live in a temp
directory that is deleted before the function returns, so the control can never leak into the repo.

An earlier attempt used an AWS-key shape; trufflehog 3.99 did not fire on it, so the control was **wrong** —
that is exactly the failure mode the control exists to expose. Recorded here rather than quietly replaced.

---

## 3. The six allowlisted shapes — every one inspected

gitleaks initially reported **25** shapes. All 25 were inspected individually; none is a credential.

| Finding | Where | What it actually is | Disposition |
|---|---|---|---|
| `AGENTKEYS_SCOPED_TOKEN': '<32 hex>'` ×5 distinct values | `field-test/v0.1.0/results/FT-CL-ENV/**`, `FT-ST-NOSECRET/**`, `harness-smoke/FT-ST-NOSECRET/**` | the **planted env token** the M14 env-virtualization case proves was delivered to a child process | allowlisted **by exact value** (5 values) |
| `private-key` | `tests/fixtures/scan_repo/keys/deploy_key.pem` | fixture body decodes to `FAKE-PRIVATE-KEY-MATERIAL-ONLY-DOM-NOT-USE` | allowlisted **by that one path** |

Two properties keep the allowlist honest, both asserted by tests:

1. **No wildcards, no shapes.** Each token entry is a literal 32-hex value (`test_the_allowlist_is_by_value_not_by_wildcard`).
   A real token has a different value and is still caught **inside the same file**.
2. **The one path entry stays fake.** `test_the_scan_fixture_private_key_is_a_stated_fake` decodes the PEM and fails
   if it ever stops being an explicit fake.

A new planted value in a future run **fails the audit** until a human adds it deliberately. That is the intended
behaviour: each new synthetic secret is a reviewed decision, not an automatic pass.

---

## 4. Generated trees are excluded, source is not

`.trufflehog-exclude.txt` skips `.git/`, `.venv/`, `node_modules/`, `__pycache__/`, tool caches, `dist/`,
`build/`. Before the exclusion, the tree scan was walking an installed virtualenv and pytest caches — noise that
says nothing about this repo. The exclusion list is asserted never to name a first-party source directory.

---

## 5. Remediation policy (unchanged, and why)

If a **live** credential is ever found:

1. **Rotate it first.** The token is already compromised the moment it is readable.
2. **Fix forward** in a new commit.
3. **Never rewrite pushed/shared history** to scrub it. The scrub buys no security and breaks every clone, branch
   and CI cache. This is codified after a prior incident ([`AGENTS.md`](../../../AGENTS.md) violation log).

This audit automates *detection only*. Nothing in the code path can rewrite history.

---

## 6. Honest limits

- Scanners find credential **shapes**. A live credential with no recognisable shape is not caught by entropy or
  rules; the ledger/redaction invariants (R6, [PRD 06 §5](../../prd/06-security-baseline.md)) are what keep
  secrets out of stored artefacts in the first place.
- The result reflects the pinned scanner versions above; a new credential format needs a scanner update.
- The history scan covers refs reachable in this clone. A fork held elsewhere is outside its reach.
- **This is not a penetration test, a dependency CVE audit, or a compliance certification.** It answers one
  question: is a live credential readable anywhere a stranger can read it?
