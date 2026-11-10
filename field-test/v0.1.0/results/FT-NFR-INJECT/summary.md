# FT-NFR-INJECT — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 1ms
- detail: env p99=0.001ms, header p99=0.001ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| env-p99-under-10ms | lte | `10.0` | `0.001` | yes |
| header-p99-under-10ms | lte | `10.0` | `0.001` | yes |
