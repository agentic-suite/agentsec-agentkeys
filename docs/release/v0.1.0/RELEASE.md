# Release — v0.1.0 (`15.5`)

**BLUF:** the artefacts are prepared and verified; **the irreversible steps are BLOCKED awaiting the
maintainer's explicit go-ahead**. Nothing in this repository will tag or publish on its own.

- **Prepared:** SBOM ([SBOM.cdx.json](SBOM.cdx.json)), sdist + wheel, the release-notes draft, the audit,
  the claims ledger, the compatibility matrix.
- **Blocked:** Sigstore/SLSA signing, `v0.1.0` tag, PyPI upload — credentials + a human decision.
- **Gate order:** audit green → claims green → compat green → notes green → **then** tag → **then** publish.

---

## 1. What is already done

| Step | Command | Result |
|---|---|---|
| SBOM (CycloneDX 1.5) | `python -m agentkeys.release sbom --write` | [SBOM.cdx.json](SBOM.cdx.json) — 0 components, stdlib-only, asserted to contain no secret shapes |
| Security audit | `python -m agentkeys.release audit --root .` | exit 0 — 0 verified in tree + full history, control fired ([SECURITY_AUDIT.md](SECURITY_AUDIT.md)) |
| Claims lint | `python -m agentkeys.release claims --root .` | exit 0 — 18 claims, 0 over-claims ([CLAIMS_LINT.md](CLAIMS_LINT.md)) |
| Compatibility | `python -m agentkeys.release compat --root . --write` | [COMPATIBILITY.md](COMPATIBILITY.md) — no "supported" without a green pack |
| Release notes | — | [RELEASE_NOTES.md](RELEASE_NOTES.md) |
| OpenSSF Scorecard | `.github/workflows/scorecard.yml` | workflow exists; the badge/result must be read from the default branch after merge |

## 2. BLOCKED — signing, tag, publish

| Step | Why it is blocked | What is required |
|---|---|---|
| **Sigstore / SLSA signing** | needs a signing identity (OIDC or key) and network egress; cannot be produced truthfully here | run the signing job in CI with `id-token: write`, or provide a key |
| **`v0.1.0` tag** | irreversible, and the milestone gates (`15.T/15.C/15.L/15.CR/15.D`) must be green on the release commit first | explicit maintainer go-ahead |
| **PyPI publish** | irreversible and public; needs `PYPI_API_TOKEN` / trusted publishing | explicit maintainer go-ahead after the artifacts verify |

**If signing is unavailable, the tag must carry that stated limitation** — "signed release" is a claim, and a
claim we cannot evidence must not be made ([PRD 20 §6](../../prd/20-standards-and-claims.md)).

## 3. The exact commands (for the human who runs them)

```sh
# 1. artefacts (already reproducible locally)
python -m build                      # dist/agentsec_agentkeys-0.1.0-{sdist.tar.gz,py3-none-any.whl}
python -m agentkeys.release sbom --write

# 2. verify the artefacts before anything irreversible
python -m zipfile -l dist/*.whl | head
python -m tarfile -l dist/*.tar.gz | head

# 3. sign (CI with OIDC, or cosign with a key)
cosign sign-blob --bundle dist/agentsec_agentkeys-0.1.0-py3-none-any.whl.bundle dist/*.whl

# 4. tag — only after the gates are green
git tag -s v0.1.0 -m "agentkeys v0.1.0"
git push origin v0.1.0

# 5. publish — only after the tag exists and the artefacts verify
python -m twine upload dist/*
```

## 4. Remediation policy (unchanged)

If a live credential is ever found in the tree **or in history**: **rotate it first**, then **fix forward** in a
new commit. **Never rewrite pushed/shared history** — the scrub buys no security and breaks every clone and CI
cache. See [`AGENTS.md`](../../../AGENTS.md).

## 5. What must be true before the tag

- [ ] `15.1`–`15.4` green (audit, claims, compat, notes)
- [ ] `15.6` risk re-grade written
- [ ] `15.7` demos green on the release commit; README/docs reflect the built core
- [ ] `15.T` full suite green · `15.C` coverage ≥95% · `15.L` ruff + `mypy --strict` clean · `15.CR` no open
      findings · `15.D` docs + PRD 12 rows closed
- [ ] the `[0.1.0]` CHANGELOG entry added (it may only appear after the exit gate passes)
