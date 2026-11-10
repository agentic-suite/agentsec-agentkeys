# FT-DK-SINGLEWRITER — PASS

- pack: `docker` · scenario: `None` · class: `P/F`
- driver: `compose-run` · duration: 2515ms
- detail: a second broker on the same home is refused

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| second-writer-refused | eq | `0` | `0` | yes |
| no-secret | eq | `()` | `()` | yes |
