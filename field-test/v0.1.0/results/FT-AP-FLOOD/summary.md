# FT-AP-FLOOD — PASS

- pack: `attack` · scenario: `None` · class: `P/F`
- driver: `flood` · duration: 4ms
- detail: flood is exactly-once; no bypass under load

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| exactly-once-under-flood | eq | `1` | `1` | yes |
| one-issuance-row | eq | `1` | `1` | yes |
| probes-still-refused | eq | `5` | `5` | yes |
