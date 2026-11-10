# FT-DK-QUICKSTART — PASS

- pack: `docker` · scenario: `SC-01` · class: `P/F`
- driver: `compose-run` · duration: 504ms
- detail: quickstart broker step runs inside the broker container

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| container-run | eq | `0` | `0` | yes |
| no-secret | eq | `()` | `()` | yes |
