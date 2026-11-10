# FT-NFR-BACKEND — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 4ms
- detail: file backend p99=0.017ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| file-p99-under-1ms | lte | `1.0` | `0.017` | yes |
| resolved | present | `True` | `True` | yes |
