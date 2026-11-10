# FT-LA-EXPORT — PASS

- pack: `audit` · scenario: `SC-29` · class: `P/F`
- driver: `export` · duration: 2ms
- detail: export is deterministic, ordered, and chain-joined

| assertion | kind | expected | actual | passed |
|---|---|---|---|---|
| deterministic | true | `True` | `True` | yes |
| ordered | eq | `[1, 2, 3]` | `[1, 2, 3]` | yes |
| chain-intact | true | `True` | `True` | yes |
| joins-by-session | eq | `3` | `3` | yes |
