# FT-NFR-COLDSTART — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 385ms
- detail: import+CLI cold start p99=58.555ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| coldstart-under-200ms | lte | `200.0` | `58.555` | yes |
| samples | eq | `5` | `5` | yes |
