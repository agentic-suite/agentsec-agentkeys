# FT-NFR-RESTART — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 1ms
- detail: start-to-serving 1.306ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| restart-under-1s | lte | `1000.0` | `1.306` | yes |
| clean-stop | eq | `absent` | `absent` | yes |
