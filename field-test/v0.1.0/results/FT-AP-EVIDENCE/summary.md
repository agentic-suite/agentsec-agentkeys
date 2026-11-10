# FT-AP-EVIDENCE — PASS

- pack: `attack` · scenario: `SC-43` · class: `P/F`
- driver: `evidence` · duration: 0ms
- detail: evidence scanner is clean and its seeded control fires

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| clean-ok | true | `True` | `True` | yes |
| clean-rows | gte | `2` | `2` | yes |
| seeded-fails | true | `True` | `True` | yes |
| seeded-location | contains | `ledger:` | `ledger:3` | yes |
