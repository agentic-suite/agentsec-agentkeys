# FT-LA-TAMPER — PASS

- pack: `audit` · scenario: `SC-30` · class: `P/F`
- driver: `verify-chain` · duration: 3ms
- detail: a rewritten ledger row is detected at its seq

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| detected | true | `True` | `True` | yes |
| names-seq | eq | `2` | `2` | yes |
