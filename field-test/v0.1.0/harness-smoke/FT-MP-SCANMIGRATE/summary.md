# FT-MP-SCANMIGRATE — PASS

- pack: `migrate` · scenario: `SC-51` · class: `P/F`
- driver: `scan-migrate` · duration: 4ms
- detail: 100% recall, 0 printed, finding closed, broad reuse flagged

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| recall | gte | `7` | `8` | yes |
| value-gone-from-file | true | `True` | `True` | yes |
| value-in-backend | true | `True` | `True` | yes |
| finding-closed | true | `True` | `True` | yes |
| zero-printed | true | `True` | `True` | yes |
| broad-reuse-flagged | gte | `1` | `3` | yes |
