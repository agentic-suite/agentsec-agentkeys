# Field-test harness — runner, deep validation, Docker, and persistence

**Status:** implemented (`14.1`); the pack results in `field-test/v0.1.0/results/` are produced by this harness.
Plan: [FIELD_TEST_PLAN.md](FIELD_TEST_PLAN.md) · Report (hand-maintained): `FIELD_TEST_REPORT.md` ·
Trace: [TRACEABILITY.md](TRACEABILITY.md).

## Layout

| Path | What |
|---|---|
| `field-test/v0.1.0/cases.yaml` | the frozen 74-case inventory (id, pack, scenario, class, env, driver) |
| `src/agentkeys/fieldtest/` | registry, executors (`packs_*.py`), runner, deep-validation gates, guards, trace |
| `scripts/fieldtest/run_pack.py` | run a pack/case |
| `scripts/fieldtest/check_grounding.py` | re-derive every assertion from the committed results |
| `scripts/fieldtest/scan_results.py` | leak gate over the results |
| `scripts/fieldtest/collect_results.py` | per-pack and total verdict counts |
| `scripts/fieldtest/trace.py` | plan → case → result → report-row trace |
| `scripts/fieldtest/verify_harness.py` | prove the gates reject bad results (self-test) |
| `scripts/fieldtest/build_report.py` | generated draft only; refuses the hand-maintained report |
| `field-test/v0.1.0/docker/` | non-root broker/child images, compose topology, fake upstream, fixture child |
| `field-test/v0.1.0/results/<case>/` | the committed evidence: `summary.json`, `summary.md`, `assertions.json`, `env.json`, `commands.log` |
| `field-test/v0.1.0/harness-smoke/` | the local smoke run (5 iterations, no Docker) proving the harness works |

## Run

```bash
# Docker topology (the field run)
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml up -d broker upstream
python scripts/fieldtest/run_pack.py --pack all --results field-test/v0.1.0/results

# local smoke (no Docker; docker cases are NOT RUN, never PASS)
python scripts/fieldtest/run_pack.py --pack all --results field-test/v0.1.0/harness-smoke \
  --no-docker --iterations 5

# gates
python scripts/fieldtest/verify_harness.py
python scripts/fieldtest/check_grounding.py --results field-test/v0.1.0/results
python scripts/fieldtest/scan_results.py --path field-test/v0.1.0/results
python scripts/fieldtest/collect_results.py --results field-test/v0.1.0/results
python scripts/fieldtest/trace.py --results field-test/v0.1.0/results
```

Equivalent: `python -m agentkeys.fieldtest <run|validate|scan|collect|trace|build-report|verify-harness>`.

## What "deep validation" means here

A result is never trusted because the runner exited 0. For every committed case:

1. **Metadata** must match `cases.yaml` (case id, pack, class) — an unknown or renamed case is a finding.
2. **Every assertion** is re-derived from its `kind` + `expected` + `actual`; a stored `passed` that does
   not match the re-derivation is a finding.
3. **Minimum depth:** blocking cases need ≥3 assertions, standard cases ≥2; a PASS with no assertions,
   a failed assertion, or no detail is a finding.
4. **Evidence integrity:** every PASS must name evidence files whose sha256 matches the committed bytes.
5. **Honesty rules:** WARN needs a named limitation and a class that allows it; a blocking case may not
   WARN or be NOT RUN; NOT RUN needs a reason.
6. **Leak gate:** no credential shape may appear in any committed file.
7. **Trace:** every `cases.yaml` case has a result and a row in the hand-maintained report; every result
   maps back to a case.

`verify_harness.py` proves the gates by feeding them deliberately broken results (ungrounded, mismatched,
WARN without limitation, seeded secret, marked file) and requiring rejection.

## Persistence in GitHub

- Results are committed under `field-test/v0.1.0/results/` (never under `docs/`).
- `.github/workflows/field-test.yml` (`workflow_dispatch`) builds the Docker topology, runs the chosen
  pack, runs all gates, uploads a results artefact (365-day retention), and pushes the results to a
  `field-test/v0.1.0-results-<run-id>` branch.
- The hand-maintained report is **never** written by the harness or CI; only the human edits it.

## Honest limits of the current smoke

`field-test/v0.1.0/harness-smoke/` was produced with `--no-docker --iterations 5`: it proves the runner,
assertions, grounding, leak gate, and trace wiring. It is **not** the field result — the seven `FT-DK-*`
cases are NOT RUN there, the kill-time iteration count is 5, and no real harness was present (two `WARN`).
The release run is the CI/Docker run with `--iterations 100`.
