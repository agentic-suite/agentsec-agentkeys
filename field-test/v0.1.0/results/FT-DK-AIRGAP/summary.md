# FT-DK-AIRGAP — FAIL

- pack: `docker` · scenario: `SC-39` · class: `P/F`
- driver: `compose-run` · duration: 390ms
- detail: offline pack passes in a --network none container

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| airgap-run | eq | `0` | `1` | NO |
| no-secret | eq | `()` | `()` | yes |
