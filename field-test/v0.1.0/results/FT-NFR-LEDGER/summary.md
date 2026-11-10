# FT-NFR-LEDGER — PASS

- pack: `nfr` · scenario: `None` · class: `P/F`
- driver: `timing` · duration: 1ms
- detail: ledger append p99=0.012ms

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| ledger-append-under-2ms | lte | `2.0` | `0.012` | yes |
| appends | eq | `200` | `200` | yes |
