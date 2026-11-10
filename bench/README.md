# agentkeys benchmark pack — v0.1.0

> **Status: published (M14 `14.8`).** Machine-readable results in
> [`results/killtime-contextdump.json`](results/killtime-contextdump.json). This is the artifact a third party
> re-runs to move a claim from *field-tested* to *verified*
> ([PRD 21 §6](../docs/prd/21-evidence-register-and-method.md)).

Two headline claims, one re-runnable pack:

| Claim | Case | Result |
|---|---|---|
| `revoke` kills access **≤1s end-to-end**, replay-verified | FT-RK-KILLTIME | p50 0.012ms · p95 0.017ms · max 0.031ms over N=100/scope; 100/100 replays refused |
| A full context dump finds **0 usable credentials**; the evidence scanner finds 0 secrets | FT-AP-CONTEXTDUMP, FT-AP-EVIDENCE | 0 usable; seeded falsification controls fire |

## Re-run it

```bash
# from the repo root, with .venv built (make setup)
.venv/bin/python -m agentkeys.bench.killtime --iterations 100          # the kill-time half
python scripts/fieldtest/run_pack.py --pack attack --results field-test/v0.1.0/results   # the zero-secret half
python scripts/fieldtest/check_grounding.py --results field-test/v0.1.0/results          # re-derive every assertion
python scripts/fieldtest/scan_results.py --path field-test/v0.1.0/results                # leak gate
```

Docker form (the reference topology):

```bash
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml run --rm broker \
  python /work/scripts/fieldtest/run_pack.py --pack killtime --results /results
```

## Pinned environment (this run)

- **Machine class:** macOS 26.6.2, arm64 (Apple Silicon) — recorded per case in each `env.json`.
- **Python:** 3.14.5 (repo `.venv`).
- **Docker:** 29.5.2 · Compose v5.6.1.
- **Git SHA:** `7b9f46e` (see the JSON's `git_sha`).
- **Network:** not required for the kill-time or context-dump halves (the offline leg runs with sockets
  disabled).

## What the JSON contains

`format` (`agentkeys-bench/1.0`), `release`, `git_sha`, `machine` (platform/system/arch/python/docker),
`generated_at`, and per claim the committed `assertions` array — so a third party can diff **expected vs
actual** field by field, not just compare a headline.

## Filing a divergent result

Open an issue titled `bench: divergent result (<claim>, <machine class>)` with:

1. your `git_sha` and machine class,
2. the raw output of the two commands above,
3. the diff against this pack's JSON.

A **slower** number is a valid result and stays published; it does not block a release unless it exceeds the
≤1s budget (p95 **and** max). A **context-dump hit** (any usable credential) is a release blocker, reported
with the variant and the masked evidence — never the value.

## Honest labels

Both claims are **field-tested** here (a human-entered verdict against committed evidence). They become
**verified** only when an independent party re-runs and reproduces them. Until then, this pack is the method;
the report is the proof.
