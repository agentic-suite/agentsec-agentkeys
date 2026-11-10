# FT-NFR-COLDSTART — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 365ms
- detail: import+CLI cold start p99=54.281ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| coldstart-under-200ms | lte | `200.0` | `54.281` | yes |
| samples | eq | `5` | `5` | yes |
