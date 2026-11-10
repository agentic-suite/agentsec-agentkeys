# FT-DK-AIRGAP — PASS

- pack: `docker` · scenario: `SC-39` · class: `P/F`
- driver: `compose-run` · duration: 633ms
- detail: offline pack passes in a --network none container

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| airgap-run | eq | `0` | `0` | yes |
| no-secret | eq | `()` | `()` | yes |
