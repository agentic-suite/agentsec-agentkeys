# FT-NFR-INJECT — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 1ms
- detail: env p99=0.003ms, header p99=0.002ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| env-p99-under-10ms | lte | `10.0` | `0.003` | yes |
| header-p99-under-10ms | lte | `10.0` | `0.002` | yes |
