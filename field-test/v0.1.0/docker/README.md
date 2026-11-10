# Field-test Docker topology (M14)

`docker compose -f field-test/v0.1.0/docker/compose.yaml ...`

## Services

| Service | Purpose | Notes |
|---|---|---|
| `broker` | runs the CLI and the packs; owns the store + credentials volumes | non-root `10001`, repo mounted read-only at `/work`, results at `/results` |
| `child` | fixture stdio MCP server in **its own container** | receives only `AGENTKEYS_SCOPED_TOKEN`; no store/credentials mount |
| `upstream` | fake HTTP resource + fake RFC 8693 STS | records metadata + sha256 only, never a token |
| `airgap` | `network_mode: none` client | proves SC-39 |
| `scan` | evidence scanner over the broker volumes | SC-31/43 |

## Build and run

```bash
docker compose -f field-test/v0.1.0/docker/compose.yaml build
docker compose -f field-test/v0.1.0/docker/compose.yaml up -d broker upstream
docker compose -f field-test/v0.1.0/docker/compose.yaml run --rm broker \
  python /work/scripts/fieldtest/run_pack.py --pack core --results /results
docker compose -f field-test/v0.1.0/docker/compose.yaml down
```

The broker image is pinned by tag here; for a reproducible published run pass a digest:
`docker build --build-arg PYTHON_IMAGE=python:3.12-slim@sha256:<digest> ...` and record it in the result
`env.json` (FT-DK-IMAGE asserts the recorded digest).

## Safety

- Non-root everywhere; the child container has **no path** to the store or the credential file.
- The `fieldtest` network is `internal`; only `upstream` is reachable. `airgap` has no network at all.
- Nothing writes a secret: fixtures are fake, and the upstream records hashes, not values.
- Results are written to `field-test/v0.1.0/results/` only; the runner refuses `docs/` and any
  `HAND-MAINTAINED` file.
